from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import yt_dlp
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_file(self, filepath: str, format_type: str, websocket: WebSocket):
        try:
            # 파일 메타데이터 전송
            metadata = {
                "type": "metadata",
                "filename": os.path.basename(filepath),
                "format": format_type
            }
            await websocket.send_text(json.dumps(metadata))

            # 파일 데이터 전송
            with open(filepath, "rb") as file:
                while chunk := file.read(1024 * 1024):  # 1MB chunk로 전송
                    await websocket.send_bytes(chunk)
            
            # 전송 완료 메시지
            await websocket.send_text(json.dumps({"type": "complete"}))
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"error: {str(e)}"
            }))

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                request = json.loads(data)
                url = request.get('url')
                format_type = request.get('format', 'mp3')
                request_type = request.get('type')

                if not url:
                    await manager.send_personal_message("URL is required", websocket)
                    continue
                
                # 플레이리스트 처리
                if request_type == 'playlist':
                    await manager.send_personal_message("플레이리스트 처리 중...", websocket)
                    
                    # 플레이리스트에서 영상 URL만 추출하는 옵션
                    playlist_opts = {
                        'quiet': True,
                        'extract_flat': 'in_playlist',
                        'skip_download': True,
                        'no_warnings': True,
                    }
                    
                    try:
                        with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                            print(f"Extracting playlist: {url}")
                            playlist_info = ydl.extract_info(url, download=False)
                            videos = []
                            
                            # 플레이리스트 항목 추출
                            if 'entries' in playlist_info:
                                for entry in playlist_info['entries']:
                                    if entry:
                                        if 'id' in entry:
                                            videos.append(f"https://www.youtube.com/watch?v={entry['id']}")
                                            print(f"Added video: {entry['id']}")
                                        elif 'url' in entry:
                                            videos.append(entry['url'])
                                            print(f"Added video by URL: {entry['url']}")
                            
                            print(f"Found {len(videos)} videos in playlist")
                            
                            # 클라이언트에 비디오 URL 목록 전송
                            response = {
                                "type": "playlist_videos",
                                "videos": videos
                            }
                            
                            await manager.send_personal_message(json.dumps(response), websocket)
                            continue
                    except Exception as e:
                        print(f"Playlist extraction error: {str(e)}")
                        await manager.send_personal_message(f"플레이리스트 처리 오류: {str(e)}", websocket)
                        continue
                
                ydl_opts = {
                    'outtmpl': 'downloads/%(title).50s.%(ext)s',
                    'restrictfilenames': False,
                    'windowsfilenames': True,
                    'force_filename': True,
                }

                if format_type == 'mp3':
                    print("mp3 download start")
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [
                            {
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                            },
                            {
                                'key': 'EmbedThumbnail',
                                'already_have_thumbnail': False,
                            },
                            {
                                'key': 'FFmpegMetadata',
                                'add_metadata': True,
                            },
                        ],
                        'writethumbnail': True,
                        'prefer_ffmpeg': True,
                        'audioquality': '0',
                    })
                elif format_type == 'mp4':
                    print("mp4 download start")
                    ydl_opts.update({
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    })
                else:
                    await manager.send_personal_message("only mp3 or mp4", websocket)
                    continue

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    if format_type == 'mp3':
                        filename = filename.rsplit('.', 1)[0] + '.mp3'
                    
                    await manager.send_personal_message(f"download complete: {filename}", websocket)
                    
                    await manager.send_file(filename, format_type, websocket)

            except Exception as e:
                await manager.send_personal_message(f"에러 발생: {str(e)}", websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("Client disconnected")

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 download 폴더 생성"""
    os.makedirs("downloads", exist_ok=True)
    

@app.get("/")
async def root():
    return "ga111o!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=53241, reload=True)

import os
import uuid
import shutil
from typing import Dict, Any, Optional
import yt_dlp
import logging

# 로그 설정 - 수정된 부분
logger = logging.getLogger(__name__)
# 기본 로깅 설정(root logger)은 스크립트가 모듈로 임포트될 때 필요 없음
# 아래 코드를 주석 처리 또는 제거
# logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.DEBUG)  # 디버그 레벨 설정
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 핸들러 추가 (콘솔 출력용)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 다운로드 파일을 저장할 임시 디렉토리
TEMP_DOWNLOAD_DIR = "temp_downloads"
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# 다운로드 상태 저장용 딕셔너리
download_status: Dict[str, Dict[str, Any]] = {}

def cleanup_file(file_path: str) -> None:
    """백그라운드에서 파일 정리"""
    logger.info(f"파일 정리 시작: {file_path}")

    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"파일 정리 완료: {file_path}")
    else:
        logger.info(f"파일 정리 완료: {file_path} (파일이 존재하지 않음)")
    
    # 해당 다운로드 ID의 상태 정보 삭제
    for download_id, status_info in list(download_status.items()):
        if status_info.get("file_path") == file_path:
            logger.info(f"다운로드 ID: {download_id} 삭제")
            del download_status[download_id]

def start_download(url: str, format: str = "mp3") -> Dict[str, Any]:
    """YouTube URL에서 음원 다운로드를 시작"""
    logger.info(f"다운로드 시작: {url}")
    download_id = str(uuid.uuid4())
    download_path = os.path.join(TEMP_DOWNLOAD_DIR, download_id)
    os.makedirs(download_path, exist_ok=True)
    
    # 다운로드 상태 초기화
    download_status[download_id] = {
        "status": "processing",
        "file_path": None
    }
    logger.info(f"다운로드 상태 초기화: {download_status[download_id]}")
    
    try:
        # 파일명 길이 제한 함수 (이 방식으로는 제대로 작동하지 않음)
        # def limit_filename_length(info):
        #     title = info.get('title', 'audio')
        #     # 파일명 최대 길이 제한 (확장자와 경로 고려하여 여유 있게 설정)
        #     max_length = 50
        #     if len(title) > max_length:
        #         title = title[:max_length] + "..."
        #     return title
        
        # yt-dlp 옵션 설정
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format,
                'preferredquality': '192',
            }],
            # 'outtmpl' 설정을 변경하여 파일명 길이 문제 해결
            'outtmpl': os.path.join(download_path, '%(id)s.%(ext)s'),
            'quiet': True,
            # 파일명 처리를 위한 콜백은 제거
            # 'parse_metadata': limit_filename_length
        }
        logger.info("ydl_opts set")
        
        # 다운로드 실행
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("ydl start")
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')

            logger.info(f"제목: {title}")
            
            # 다운로드된 파일 경로 확인
            file_name = f"{title}.{format}"
            logger.info(f"다운로드된 파일 경로: {file_name}")
            
            # 파일이 실제로 생성되었는지 확인
            downloaded_files = os.listdir(download_path)
            if not downloaded_files:
                raise Exception("파일 다운로드에 실패했습니다.")
            
            # 실제 생성된 파일 경로
            actual_file_path = os.path.join(download_path, downloaded_files[0])
            
            # 다운로드 상태 업데이트
            download_status[download_id] = {
                "status": "completed",
                "file_path": actual_file_path,
                "title": title
            }
            
            return {
                "download_id": download_id,
                "status": "completed",
                "message": f"'{title}' 다운로드가 완료되었습니다."
            }
            
    except Exception as e:
        # 오류 발생 시 상태 업데이트
        download_status[download_id] = {
            "status": "failed",
            "error": str(e)
        }
        # 다운로드 디렉토리 정리
        shutil.rmtree(download_path, ignore_errors=True)
        raise e

def get_download_status(download_id: str) -> Dict[str, Any]:
    """다운로드 상태 조회"""
    if download_id not in download_status:
        raise KeyError("해당 다운로드 ID를 찾을 수 없습니다.")
    
    return download_status[download_id]

def get_download_file_path(download_id: str) -> str:
    """다운로드된 파일 경로 조회"""
    if download_id not in download_status:
        raise KeyError("해당 다운로드 ID를 찾을 수 없습니다.")
    
    status_info = download_status[download_id]
    
    if status_info["status"] == "failed":
        raise ValueError(f"다운로드 실패: {status_info.get('error', '알 수 없는 오류')}")
    
    if status_info["status"] != "completed":
        raise ValueError("다운로드가 아직 진행 중입니다.")
    
    file_path = status_info.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("파일을 찾을 수 없습니다.")
    
    return file_path

def cleanup_temp_directory() -> None:
    """임시 디렉토리 정리"""
    if os.path.exists(TEMP_DOWNLOAD_DIR):
        shutil.rmtree(TEMP_DOWNLOAD_DIR, ignore_errors=True)
    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True) 
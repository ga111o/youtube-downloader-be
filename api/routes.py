from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os

from schemas.models import DownloadRequest, DownloadResponse
import services.downloader as downloader_service

router = APIRouter()

@router.post("/download", response_model=DownloadResponse)
async def download_audio(request: DownloadRequest):
    """YouTube URL에서 음원 다운로드를 시작하는 엔드포인트"""
    try:
        result = downloader_service.start_download(str(request.url), request.format)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다운로드 실패: {str(e)}")

@router.get("/status/{download_id}")
async def check_status(download_id: str):
    """다운로드 상태 확인 엔드포인트"""
    try:
        return downloader_service.get_download_status(download_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{download_id}")
async def get_file(download_id: str, background_tasks: BackgroundTasks):
    """다운로드한 파일을 제공하는 엔드포인트"""
    try:
        file_path = downloader_service.get_download_file_path(download_id)
        
        # 파일 다운로드 후 자동 정리 예약
        background_tasks.add_task(downloader_service.cleanup_file, file_path)
        
        return FileResponse(
            path=file_path, 
            filename=os.path.basename(file_path),
            media_type="audio/mpeg"
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        if "진행 중" in str(e):
            raise HTTPException(status_code=202, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
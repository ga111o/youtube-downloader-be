from typing import Optional
from pydantic import BaseModel, HttpUrl

class DownloadRequest(BaseModel):
    url: HttpUrl
    format: Optional[str] = "mp3"  # 기본 포맷은 mp3

class DownloadResponse(BaseModel):
    download_id: str
    status: str
    message: str 
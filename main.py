from fastapi import FastAPI
from api.routes import router
import services.downloader as downloader_service
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)



@app.on_event("startup")
async def startup_event():
    """앱 시작 시 임시 디렉토리 정리"""
    downloader_service.cleanup_temp_directory()

@app.get("/")
async def root():
    return "ga111o!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=53241)

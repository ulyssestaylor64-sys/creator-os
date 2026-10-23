"""
Creator OS — FastAPI 后端入口
挂载静态文件、支持 CORS、SPA fallback。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from api import routes

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Creator OS API",
    version="2.4.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env.strip():
    _allow_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    # 默认只放开本地调试端口；线上同源部署，不需要额外放行
    _allow_origins = [
        "http://localhost:8000", "http://127.0.0.1:8000",
        "http://localhost:8001", "http://127.0.0.1:8001",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 /api 路由
app.include_router(routes.router)

# 挂载静态文件
app.mount("/_shared", StaticFiles(directory=BASE_DIR / "_shared"), name="shared")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    # API 未命中由路由处理；其余页面返回 index.html
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}
    file_path = BASE_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(BASE_DIR / "index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)

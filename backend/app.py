from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

import api as api_module
from database import init_db

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


def create_app() -> FastAPI:
    """
    创建FastAPI应用，配置启动时初始化数据库，
        添加允许跨域及开发环境禁用缓存的中间件，
        注册API路由，并在前端目录存在时挂载静态文件服务，
        最后返回配置好的应用实例。
    """
    app = FastAPI(title="Cute Cat Bot API")

    @app.on_event("startup")
    async def _startup_init_db():
        init_db()
    # CORS（Cross-Origin Resource Sharing，跨域资源共享）中间件是一种安全机制，
    #   用于控制浏览器如何允许或阻止来自不同源（域名、协议或端口）的网页访问后端 API
    # 解除跨域限制，让前端可以顺利与后端通信：
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # No-cache middleware for development
    @app.middleware("http")
    async def _no_cache(request, call_next):
        """
        定义了一个HTTP中间件，用于开发环境禁用缓存:
            它拦截请求，对根路径及HTML、JS、CSS文件响应添加no-cache等头部信息，
            强制浏览器不缓存这些资源，确保前端开发时能实时获取最新文件。
        """
        response = await call_next(request)
        path = request.url.path or ""
        if path == "/" or path.endswith((".html", ".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.include_router(api_module.router)

    # serve frontend static files at root
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))

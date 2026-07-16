from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from routers import admin, auth, chat, knowledge
from schemas import ErrorResponse


def create_app() -> FastAPI:
    """
    创建FastAPI应用，配置启动时初始化数据库，
        添加允许跨域及开发环境禁用缓存的中间件，
        注册API路由，并在前端目录存在时挂载静态文件服务，
        最后返回配置好的应用实例。
    """
    app = FastAPI(title="Cute Cat Bot API")

    # CORS — 从环境变量读取允许的来源，生产和开发模式可分别配置
    ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
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

    # Global exception handlers — unified error response format
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.status_code, message=exc.detail).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(code=50000, message=f"服务器内部错误: {str(exc)}").model_dump(),
        )

    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(knowledge.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))

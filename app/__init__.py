from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app():
    app = FastAPI()

    # 添加CORS中间件,允许所有来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 导入并注册路由
    from app.routes import router as main_router
    app.include_router(main_router)


    return app

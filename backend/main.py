# 运行入口，实例化FastAPI，路由分发
import logging

from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from config import INDEX_DIR, BASE_DIR
from logging_config import setup_logging
from services.rag import RAG
from database import init_db
from fastapi import FastAPI   # 从 fastapi 导出 FastAPI 类
import uvicorn                # 导入 web 服务器
import os

# 引入路由
from api.documents import router as doc_router
from api.analysis import router as analysis_router
from api.agent import router as agent_router
from api.qa import router as qa_router

# 统一日志：控制台 + backend/logs/app.log（只在这里调用一次）
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    app.state.rag_service = RAG()
    logger.info("RAG 服务已就绪（等待按需索引）")

    # 索引文件可能损坏（np.save 不是原子写，写到一半被杀就会坏）。
    # 这里必须兜住，否则整个服务都起不来。
    try:
        loaded = app.state.rag_service.load_index(INDEX_DIR)
    except Exception as e:
        logger.error("索引加载失败（已忽略，请到「文档管理」页重新建立索引）：%s", e)
        # 加载失败时 store 里可能只填了一半，直接换一个干净的，避免后面检索时下标越界
        app.state.rag_service = RAG()
        loaded = False

    if loaded:
        logger.info("索引加载成功，共 %d 个片段", len(app.state.rag_service.store))
    else:
        logger.info("未发现已有索引，等待文档上传后按需建立")

    init_db()
    logger.info("数据库初始化成功")

    yield  # 💡 服务运行期间会停在这里
    # 关闭时执行
    app.state.rag_service = None
    logger.info("应用关闭")

# 在创建 app 实例时挂载它
app = FastAPI(
    title="AI 文档助手",
    lifespan=lifespan,
    # 💡 指向本地的静态文件（前提是你在 backend 目录下建了 static 文件夹并放入了文件）
    swagger_ui_parameters={
        "swagger_js_url": "/static/swagger-ui-bundle.js",
        "swagger_css_url": "/static/swagger-ui.css",
        "swagger_favicon_url": "/static/favicon-32x32.png",
    }
)

# 💡 挂载静态文件目录
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(doc_router, prefix="/documents", tags=["文件处理"])
app.include_router(analysis_router, prefix="/analysis", tags=["ai分析"])
app.include_router(qa_router, prefix="/qa", tags=["ai文档追问"])
app.include_router(agent_router, prefix="/agent", tags=["调用agent"])

# 路由
@app.get("/health")
async def root():
    return {"message": "Hello FastAPI"}


# 启动项目
if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=False)

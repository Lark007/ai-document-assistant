# 对于文件的各种操作，上传、获取等

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from database import get_db
from config import INDEX_DIR
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)


# 上传文件，返回文件预览、ID等信息
@router.post("/upload")
async def upload_document(file: UploadFile = File(...), request: Request = None):

    # 1. 检查扩展名是否为 .txt 或 .md
    # 获取文件扩展名并转为小写，防止出现 .TXT 被拒绝的情况
    file_name = file.filename
    file_ext = os.path.splitext(file_name)[1].lower()

    if file_ext not in [".txt", ".md"]:
        logger.warning("上传被拒：不支持的扩展名 %s（文件名 %s）", file_ext or "（无扩展名）", file_name)
        raise HTTPException(status_code=400, detail="仅支持 .txt 或 .md 文件")

    # 2. 读取文件字节
    try:
        content_bytes = await file.read()
        # 3. 按 UTF-8 解码
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("上传被拒：文件不是 UTF-8 编码（文件名 %s）", file_name)
        raise HTTPException(status_code=400, detail="文件编码格式错误，请使用 UTF-8 编码")
    except Exception as e:
        logger.exception("读取上传文件失败（文件名 %s）", file_name)
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


    # 3. 提取文件类型 (去掉点号，例如 ".md" -> "md")
    file_type = file_ext.replace(".", "")

    # 4. 截取预览 (取前 100 个字符，防止太长)
    preview = text_content[:100]

    # 5.存入数据库
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, file_type, content) VALUES (?, ?, ?)",
            (file.filename, file_type, text_content)
        )
        conn.commit()
        document_id = cursor.lastrowid  # 💡 拿到刚插入的自增 ID

    # 6.自动索引 + 去重 + 持久化
    rag = request.app.state.rag_service
    try:
        n = rag.index_text(text_content, source=str(document_id))
        rag.save_index(INDEX_DIR)
        indexed = True
        chunks = n
    except Exception as e:
        # 索引失败不影响上传成功，但必须留下记录，方便回头到「文档管理」页手动重建索引
        logger.error("文档 %s 自动索引失败（可在文档管理页重新建立索引）：%s", document_id, e)
        indexed = False
        chunks = 0

    # 7. 返回要求的结构
    return {
        "document_id": document_id,
        "filename": file.filename,
        "file_type": file_type,
        "length": len(text_content),
        "preview": preview,
        "indexed": indexed
    }

# 根据id拿文件
@router.get("/{document_id}")
async def get_document(document_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        doc = cursor.fetchone()  # 取一条，返回sqlite3.Row 或 None

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    #  sqlite3.Row 可以像字典一样用列名取
    return {
        "document_id": doc["id"],
        "filename": doc["filename"],
        "file_type": doc["file_type"],
        "length": len(doc["content"]),
        "content": doc["content"]
    }

# 根据id拿文件名
@router.get("/name/{document_id}")
async def get_document_name(document_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        doc = cursor.fetchone()  # 取一条，返回sqlite3.Row 或 None

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    #  sqlite3.Row 可以像字典一样用列名取
    return {
        "document_id": doc["id"],
        "filename": doc["filename"]
    }

# 文档列表：给「文档管理」页面用，带索引状态
# 注意：路径写成空字符串，接口地址才是 /documents；写成 "/" 会变成 /documents/ 并触发 307 跳转
@router.get("")
async def list_documents(request: Request):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename, file_type, LENGTH(content) AS length, created_at "
            "FROM documents ORDER BY id DESC"
        )
        rows = cursor.fetchall()

        # 查看是否有分析记录
        cursor.execute(
            "SELECT DISTINCT document_id FROM analysis_records "
            "WHERE analysis_type = 'structured_output'"
        )
        analyzed_ids = {r["document_id"] for r in cursor.fetchall()}

    # 索引里现在记录了哪些 source（就是被索引过的 document_id 字符串）
    rag = request.app.state.rag_service
    sources = list(rag.store.sources) if rag else []

    return [
        {
            "document_id": row["id"],
            "filename": row["filename"],
            "file_type": row["file_type"],
            "length": row["length"],
            "created_at": row["created_at"],
            "indexed": str(row["id"]) in sources,
            "chunks": sources.count(str(row["id"])),
            "analyzed": row["id"] in analyzed_ids,
        }
        for row in rows
    ]

# 删除文档：同时删掉它的分析记录和索引片段
@router.delete("/{document_id}")
async def delete_document(document_id: int, request: Request):
    # 1. 先确认文档存在
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="文档不存在")
        filename = row["filename"]

        # 2. 删掉它的分析记录（先删子表，再删主表）
        cursor.execute("DELETE FROM analysis_records WHERE document_id = ?", (document_id,))
        # 3. 删掉文档本身
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()

    # 4. 把它从索引里删掉；没索引过就返回 0，不用白写一次磁盘
    rag = request.app.state.rag_service
    removed = rag.store.remove_by_source(str(document_id)) if rag else 0

    if removed and rag:
        if len(rag.store) == 0:
            # 片段被删光了：把索引文件一起清掉。
            # 否则 meta.json 会被写成空的、而 vectors.npy 还是旧的，
            # 下次启动 load() 发现两者数量对不上会直接报错。
            for name in ("vectors.npy", "meta.json"):
                (INDEX_DIR / name).unlink(missing_ok=True)
        else:
            rag.save_index(INDEX_DIR)

    return {
        "message": "已删除",
        "document_id": document_id,
        "filename": filename,
        "removed_chunks": removed,
    }

# 针对数据库的操作

import sqlite3
from contextlib import contextmanager

# 数据库文件路径（放在项目根目录）
DATABASE_PATH = "document.db"

# ============ 1. 创建数据库连接 ============
def get_connection():
    """创建一个新的数据库连接"""
    # check_same_thread=False 允许 FastAPI 在不同线程中使用同一个连接
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    # 让查询结果可以像字典一样通过列名访问，而不是用索引
    conn.row_factory = sqlite3.Row
    # 开启外键约束。
    # SQLite 默认是关的，而且这是"连接级"设置：每新建一个连接都要重新开一次，
    # 所以放在这里，所有通过 get_db() 拿到连接的地方都会自动生效。
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ============ 2. 初始化数据表 ============
def init_db():
    """创建所有数据表（如果不存在）"""
    conn = get_connection()
    cursor = conn.cursor()

    # 文档表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 分析记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)

    conn.commit()
    conn.close()

# ============ 3 & 4. 提供会话 + 自动关闭 ============
@contextmanager
def get_db():
    """
    上下文管理器：自动管理连接的打开和关闭。
    用法：
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    conn = get_connection()
    try:
        yield conn
    except Exception as e:
        conn.rollback()  # 出错时回滚事务
        raise e
    finally:
        conn.close()     # 💡 无论成功失败，最终都关闭连接

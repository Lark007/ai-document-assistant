# 作用：统一的日志配置
#
# 为什么单独一个文件：logging 的级别、格式、输出位置只在这里配置一次，
# 其他模块只用 `logger = logging.getLogger(__name__)` 拿 logger、然后 logger.error(...)。
#
# 三条底线：
# 1. 请求失败、模型调用失败、工具调用失败都要留下记录；
# 2. 绝对不要把 API Key 之类的内容打进日志（只记异常本身的信息）；
# 3. 日志同时写到控制台和 backend/logs/app.log，出问题可以直接翻文件。

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """在 main.py 里调用一次即可。

    重复调用不会出现重复日志（先清掉旧的 handler）。
    """
    formatter = logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.addHandler(console)

    # 单个文件最多 1MB，留 3 份备份，避免日志无限增长。
    # 万一目录建不出来或文件写不了（权限问题），不能让整个服务起不来：
    # 退化成「只打控制台」，并说明原因。
    try:
        LOG_DIR.mkdir(exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as e:
        root.warning("无法写入日志文件 %s，本次只输出到控制台：%s", LOG_FILE, e)

    # uvicorn 的访问日志自己会打一遍，关掉冒泡，避免每行出现两次
    logging.getLogger("uvicorn.access").propagate = False

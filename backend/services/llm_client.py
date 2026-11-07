# 初始化大模型客户端
import os
from dotenv import load_dotenv
from openai import OpenAI

# 关键：加载 .env 文件里的变量到 os.environ 中
load_dotenv()

# 从环境变量里安全读取（如果读不到，就是 None）
api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL")
model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 第二个参数是默认值

# 快速自检：如果 Key 没读到，直接报错，别让程序跑一半崩溃
if not api_key:
    raise ValueError("！！ 未找到 DEEPSEEK_API_KEY，请检查 .env 文件是否配置！")

# 初始化客户端（全局只创建一次即可）
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

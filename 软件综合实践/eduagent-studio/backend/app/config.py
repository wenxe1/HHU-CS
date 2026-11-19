import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/eduagent")
DATABASE_NAME = os.getenv("DATABASE_NAME", "eduagent")
DEEPSEEK_API_KEY = os.getenv("AI_DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("AI_DEEPSEEK_MODEL", "deepseek-chat")

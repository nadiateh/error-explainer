import os
import sys
from pathlib import Path

from dotenv import load_dotenv

APP_NAME = "ErrorExplainer"

if getattr(sys, "frozen", False):
    APP_DIR = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
else:
    APP_DIR = Path(__file__).resolve().parent

APP_DIR.mkdir(parents=True, exist_ok=True)

ENV_PATH = APP_DIR / ".env"
load_dotenv(ENV_PATH)

AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL")
DB_PATH = APP_DIR / "error_history.db"


def check_config():
    if not AI_API_KEY or AI_API_KEY == "paste-your-key-here":
        raise SystemExit(
            f"No API key found.\n\nPut a .env file with AI_API_KEY=your-real-key in:\n{APP_DIR}"
        )
    if not AI_MODEL:
        raise SystemExit(
            f"No model name found.\n\nAdd AI_MODEL=model-name to the .env file in:\n{APP_DIR}"
        )


if __name__ == "__main__":
    print("Settings folder:", APP_DIR)
    print("API key loaded:", "yes" if AI_API_KEY else "no")
    print("Model:", AI_MODEL or "(not set)")
    print("Database file:", DB_PATH)
import os
from dotenv import load_dotenv

load_dotenv()

AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL")
DB_PATH = "error_history.db"

def check_config():
    if not AI_API_KEY or AI_API_KEY == "key":
        raise SystemExit(
            "No API key foun. Open the .env file and set AI_API_KEY=real-key"
        )
    if not AI_MODEL or AI_MODEL == "model":
        raise SystemExit(
            "No moedl name found. Open the .env file and set AI_MODEL=model-name"
        )


if __name__ == "__main__":
    print("API key loaded:", "yes" if AI_API_KEY else "no")
    print("Model:", AI_MODEL or "(not set)")
    print("Database file:", DB_PATH)

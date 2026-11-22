from openai import OpenAI
import config

config.check_config()

client = OpenAI(api_key=config.AI_API_KEY)

def ask_ai(instructions, user_message):
    response = client.responses.create(
        model=config.AI_MODEL,
        instructions=instructions,
        input=user_message,
    )
    return response.output_text


if __name__ == "__main__":
    reply = ask_ai(
        "You are a friendly assistant. Reply in one short sentence.",
        "Say hello and confirm you are working."
    )
    print(reply)
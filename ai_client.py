from openai import OpenAI
import config
import prompts


config.check_config()

client = OpenAI(api_key=config.AI_API_KEY)

def ask_ai(instructions, user_message):
    response = client.responses.create(
        model=config.AI_MODEL,
        instructions=instructions,
        input=user_message,
    )
    return response.output_text

def explain_error(error_text):
    user_message = prompts.build_user_message(error_text)
    return ask_ai(prompts.SYSTEM_PROMPT, user_message)


if __name__ == "__main__":
    sample_error = """Traceback (most recent call last):
  File "app.py", line 3, in <module>
    print(total + 5)
NameError: name 'total' is not defined"""
    # sample_error = "Hello, how are you?"
    print(explain_error(sample_error))
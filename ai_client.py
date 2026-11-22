import openai
from openai import OpenAI
import config
import prompts


config.check_config()

client = OpenAI(api_key=config.AI_API_KEY)

class AIError(Exception):
    """Raised when the AI request fails. The message is safe to show the user."""

def ask_ai(instructions, user_message):
    try:
        response = client.responses.create(
            model=config.AI_MODEL,
            instructions=instructions,
            input=user_message,
        )

    except openai.AuthenticationError:
        raise AIError("OpenAI rejected your API key. Check AI_API_KEY in your .env file.")

    except openai.RateLimitError:
        raise AIError("Too many requests, or your account is out of credit. "
                        "Wait a moment, or check billing at platform.openai.com")

    except openai.NotFoundError:
        raise AIError(f"The model '{config.AI_MODEL}' wasn't found. Check AI_MODEL in your .env file.")

    except openai.APIConnectionError:
        raise AIError("Couldn't reach OpenAI. Check your internet connection.")

    except openai.APIError as e:
        raise AIError(f"OpenAI return an unexpected error: {e}")

    return response.output_text

def explain_error(error_text):
    user_message = prompts.build_user_message(error_text)
    reply = ask_ai(prompts.SYSTEM_PROMPT, user_message).strip()

    first_line, _, rest = reply.partition("\n")

    if first_line.strip().upper().startswith(prompts.NOT_AN_ERROR_MARKER):
        message = rest.strip() or "That doesn't look like an error message. Please paste the full error."
        return False, message

    return True, reply


if __name__ == "__main__":
    sample_error = """Traceback (most recent call last):
  File "app.py", line 3, in <module>
    print(total + 5)
NameError: name 'total' is not defined"""

    for test_input in [sample_error, "hello how are you"]:
        is_error, text = explain_error(test_input)
        print("Is it an error?", is_error)
        print(text)
        print("=" * 60)
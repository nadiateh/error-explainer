import json

import openai
from openai import OpenAI
import config
import prompts

_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.AI_API_KEY)
    return _client


class AIError(Exception):
    """Raised when the AI request fails. The message is safe to show the user."""


def ask_ai(instructions, user_message, text_format=None):
    request = {
        "model": config.AI_MODEL,
        "instructions": instructions,
        "input": user_message,
    }
    if text_format is not None:
        request["text"] = {"format": text_format}

    try:
        response = get_client().responses.create(**request)
    except openai.AuthenticationError:
        raise AIError("OpenAI rejected your API key. Check AI_API_KEY in your .env file.")
    except openai.RateLimitError:
        raise AIError("Too many requests, or your account is out of credit. "
                      "Wait a moment, or check billing at platform.openai.com.")
    except openai.NotFoundError:
        raise AIError(f"The model '{config.AI_MODEL}' wasn't found. Check AI_MODEL in your .env file.")
    except openai.APIConnectionError:
        raise AIError("Couldn't reach OpenAI. Check your internet connection.")
    except openai.APIError as e:
        raise AIError(f"OpenAI returned an unexpected error: {e}")

    if response.status != "completed":
        raise AIError("The answer was cut off before it finished. Please try again.")

    return response.output_text


def explain_error(error_text):
    user_message = prompts.build_user_message(error_text)
    reply = ask_ai(prompts.SYSTEM_PROMPT, user_message, prompts.EXPLANATION_FORMAT)

    try:
        data = json.loads(reply)
    except json.JSONDecodeError:
        raise AIError("The AI's answer couldn't be read. Please try again.")

    return data["is_error"], data


def ask_follow_up(error_text, explanation, previous_followups, question):
    conversation = [
        {"role": "user", "content": prompts.build_user_message(error_text)},
        {"role": "assistant", "content": explanation},
    ]

    for item in previous_followups:
        conversation.append({"role": "user", "content": item["question"]})
        conversation.append({"role": "assistant", "content": item["answer"]})

    conversation.append({"role": "user", "content": question})

    return ask_ai(prompts.FOLLOW_UP_PROMPT, conversation).strip()


if __name__ == "__main__":
    config.check_config()

    sample_error = """Traceback (most recent call last):
  File "app.py", line 3, in <module>
    print(total + 5)
NameError: name 'total' is not defined"""

    for test_input in [sample_error, "hello how are you"]:
        is_error, data = explain_error(test_input)
        print("Is it an error?", is_error)
        print(json.dumps(data, indent=2))
        print("=" * 60)
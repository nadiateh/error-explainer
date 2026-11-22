from ai_client import explain_error, AIError
import storage

END_WORD = "END"
QUIT_WORD = "QUIT"
DIVIDER = "-" * 60

def read_error_from_user():
    print(f"\nPaste your error below. When you're done, type {END_WORD} on its own line and press Enter.")
    print(f"(Type {QUIT_WORD} to exit.)\n")

    lines = []

    while True:
        line = input()
        command = line.strip().upper()

        if command == QUIT_WORD and not lines:
            return None

        if command == END_WORD:
            break

        lines.append(line)

    return "\n".join(lines).strip()


def main():
    storage.init_db()
    print("=== Error Explainer ===")

    while True:
        error_text = read_error_from_user()

        if error_text is None:
            print("Goodbye!")
            break

        if not error_text:
            print("Nothing was pasted. Let's try again.")
            continue

        print("\nThinking...\n")

        try:
            explanation = explain_error(error_text)

        except AIError as problem:
            print(f"Sorry, something went wrong: {problem}")

        print(DIVIDER)
        print(explanation)
        print(DIVIDER)

        entry_id = storage.save_error(error_text, explanation)
        print(f"(Saved to history as #{entry_id})")

if __name__ == "__main__":
    try:
        main()

    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
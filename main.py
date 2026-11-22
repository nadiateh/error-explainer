from ai_client import explain_error, AIError
import config
import explanation
import storage

END_WORD = "END"
CANCEL_WORD = "CANCEL"
DIVIDER = "-" * 60


# ---------- Small helpers ----------

def summary_line(error_text):
    lines = error_text.strip().splitlines()
    return lines[-1] if lines else "(empty)"


def format_time(iso_text):
    return iso_text.replace("T", " ")


def print_entry_list(entries):
    if not entries:
        print("No saved errors found.")
        return

    for entry in entries:
        summary = summary_line(entry["error_text"])[:60]
        print(f"  #{entry['id']:<4} {format_time(entry['created_at'])}   {summary}")


# ---------- Menu option 1: explain a new error ----------

def read_error_from_user():
    print(f"\nPaste your error below. When you're done, type {END_WORD} on its own line and press Enter.")
    print(f"(Type {CANCEL_WORD} to go back to the menu.)\n")

    lines = []
    while True:
        line = input()
        command = line.strip().upper()

        if command == CANCEL_WORD and not lines:
            return None
        if command == END_WORD:
            break

        lines.append(line)

    return "\n".join(lines).strip()


def explain_new_error():
    error_text = read_error_from_user()

    if error_text is None:
        print("Cancelled.")
        return

    if not error_text:
        print("Nothing was pasted.")
        return

    print("\nThinking...\n")

    try:
        is_error, data = explain_error(error_text)
    except AIError as problem:
        print(f"Sorry, something went wrong: {problem}")
        return

    if not is_error:
        print(data["summary"])
        print("(Not saved to history, because this didn't look like an error message.)")
        return

    print(DIVIDER)
    print(explanation.to_text(data))
    print(DIVIDER)

    entry_id = storage.save_error(error_text, explanation.to_saved(data))
    print(f"(Saved to history as #{entry_id})")


# ---------- Menu option 2: view recent errors ----------

def view_recent_errors():
    print("\nYour 10 most recent errors:\n")
    print_entry_list(storage.get_recent_errors(10))


# ---------- Menu option 3: open a past error ----------

def open_past_error():
    raw = input("Enter the entry number (for example 3): ").strip().lstrip("#")

    if not raw.isdigit():
        print("That's not a valid number.")
        return

    entry = storage.get_error(int(raw))

    if entry is None:
        print(f"No entry #{raw} found.")
        return

    print("\n" + DIVIDER)
    print(f"Entry #{entry['id']}   |   saved {format_time(entry['created_at'])}")
    print(DIVIDER)
    print("YOUR ERROR:\n")
    print(entry["error_text"])
    print("\n" + DIVIDER)
    print(explanation.display_text(entry["explanation"]))
    print(DIVIDER)


# ---------- Menu option 4: search history ----------

def search_history():
    search_text = input("Search for (for example NameError): ").strip()

    if not search_text:
        print("Nothing to search for.")
        return

    results = storage.search_errors(search_text)
    print(f"\nFound {len(results)} result(s) for '{search_text}':\n")
    print_entry_list(results)


# ---------- The menu itself ----------

def show_menu():
    print("\n=== Error Explainer ===")
    print("1. Explain a new error")
    print("2. View recent errors")
    print("3. Open a past error")
    print("4. Search history")
    print("5. Quit")


def main():
    config.check_config()
    storage.init_db()

    actions = {
        "1": explain_new_error,
        "2": view_recent_errors,
        "3": open_past_error,
        "4": search_history,
    }

    while True:
        show_menu()
        choice = input("Choose an option (1-5): ").strip()

        if choice == "5":
            print("Goodbye!")
            break

        action = actions.get(choice)

        if action is None:
            print("Please enter a number from 1 to 5.")
            continue

        action()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
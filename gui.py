import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from ai_client import explain_error, ask_follow_up, AIError
import config 
import explanation
import storage

FOLLOW_UP_DIVIDER = "=" * 50


def summary_line(error_text):
    lines = error_text.strip().splitlines()
    return lines[-1] if lines else "(empty)"


class ErrorExplainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Error Explainer")
        self.root.geometry("1100x750")
        self.root.minsize(800, 550)

        self.history_ids = []
        self.results = queue.Queue()
        self.current_entry_id = None

        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.build_history_panel()
        self.build_main_panel()

        self.refresh_history()

    # ---------- Building the window ----------

    def build_history_panel(self):
        panel = ttk.Frame(self.root, padding=10)
        panel.grid(row=0, column=0, sticky="nsew")

        ttk.Label(panel, text="History", font="TkHeadingFont").pack(anchor="w")

        ttk.Label(panel, text="Search:").pack(anchor="w", pady=(8, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_history())
        ttk.Entry(panel, textvariable=self.search_var).pack(fill="x", pady=(2, 8))

        self.history_list = tk.Listbox(panel, activestyle="none", exportselection=False)
        self.history_list.pack(fill="both", expand=True)
        self.history_list.bind("<<ListboxSelect>>", self.on_history_select)

        self.delete_button = ttk.Button(panel, text="Delete selected", command=self.on_delete_click)
        self.delete_button.pack(fill="x", pady=(8, 0))

    def build_main_panel(self):
        panel = ttk.Frame(self.root, padding=10)
        panel.grid(row=0, column=1, sticky="nsew")

        ttk.Label(panel, text="Paste your error:", font="TkHeadingFont").pack(anchor="w")
        self.error_box = ScrolledText(panel, height=10, wrap="word", font="TkFixedFont")
        self.error_box.pack(fill="x", pady=(5, 5))

        buttons = ttk.Frame(panel)
        buttons.pack(fill="x")
        self.explain_button = ttk.Button(buttons, text="Explain", command=self.on_explain_click)
        self.explain_button.pack(side="left")
        ttk.Button(buttons, text="Clear", command=self.on_clear_click).pack(side="left", padx=5)
        self.status_label = ttk.Label(buttons, text="")
        self.status_label.pack(side="left", padx=10)

        ttk.Label(panel, text="Explanation:", font="TkHeadingFont").pack(anchor="w", pady=(10, 0))
        self.result_box = ScrolledText(panel, height=8, wrap="word", state="disabled")
        self.result_box.pack(fill="both", expand=True, pady=(5, 0))

        ttk.Label(panel, text="Ask a follow-up question about this error:").pack(anchor="w", pady=(10, 0))
        ask_row = ttk.Frame(panel)
        ask_row.pack(fill="x", pady=(2, 0))
        self.question_var = tk.StringVar()
        question_box = ttk.Entry(ask_row, textvariable=self.question_var)
        question_box.pack(side="left", fill="x", expand=True)
        question_box.bind("<Return>", lambda event: self.on_ask_click())
        self.ask_button = ttk.Button(ask_row, text="Ask", command=self.on_ask_click)
        self.ask_button.pack(side="left", padx=(5, 0))

    # ---------- Small helpers ----------

    def show_result(self, text):
        self.result_box.config(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.config(state="disabled")

    def set_status(self, text):
        self.status_label.config(text=text)

    def set_busy(self, busy):
        new_state = "disabled" if busy else "normal"
        for button in (self.explain_button, self.ask_button, self.delete_button):
            button.config(state=new_state)
        self.set_status("Thinking..." if busy else "")

    def refresh_history(self):
        search_text = self.search_var.get().strip()
        if search_text:
            entries = storage.search_errors(search_text, limit=100)
        else:
            entries = storage.get_recent_errors(100)

        self.history_list.delete(0, "end")
        self.history_ids = []
        for entry in entries:
            self.history_list.insert("end", f"#{entry['id']}  {summary_line(entry['error_text'])}")
            self.history_ids.append(entry["id"])

    def selected_entry_id(self):
        selection = self.history_list.curselection()
        if not selection:
            return None
        return self.history_ids[selection[0]]

    def show_entry(self, entry_id):
        entry = storage.get_error(entry_id)
        if entry is None:
            return None

        self.current_entry_id = entry_id

        self.error_box.delete("1.0", "end")
        self.error_box.insert("1.0", entry["error_text"])

        text = explanation.display_text(entry["explanation"])
        for item in storage.get_followups(entry_id):
            text += f"\n\n{FOLLOW_UP_DIVIDER}\nYOU ASKED: {item['question']}\n\n{item['answer']}"
        self.show_result(text)
        self.result_box.see("end")

        return entry

    # ---------- Running AI work in the background ----------

    def run_in_background(self, task, on_done):
        def worker():
            # Runs in the background thread. No Tkinter calls allowed in here.
            try:
                result = task()
                self.results.put((on_done, result, None))
            except AIError as problem:
                self.results.put((on_done, None, str(problem)))
            except Exception as problem:
                self.results.put((on_done, None, f"Unexpected problem: {problem}"))

        self.set_busy(True)
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, self.check_for_result)

    def check_for_result(self):
        try:
            on_done, result, problem = self.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self.check_for_result)
            return

        self.set_busy(False)
        on_done(result, problem)

    # ---------- Explain ----------

    def on_explain_click(self):
        error_text = self.error_box.get("1.0", "end").strip()
        if not error_text:
            self.set_status("Paste an error first.")
            return

        self.run_in_background(
            lambda: explain_error(error_text),
            lambda result, problem: self.finish_explanation(error_text, result, problem),
        )

    def finish_explanation(self, error_text, result, problem):
        if problem:
            self.current_entry_id = None
            self.show_result(f"Sorry, something went wrong:\n\n{problem}")
            return

        is_error, data = result

        if not is_error:
            self.current_entry_id = None
            self.show_result(data["summary"])
            self.set_status("Not saved (this didn't look like an error).")
            return

        entry_id = storage.save_error(error_text, explanation.to_saved(data))
        self.refresh_history()
        self.show_entry(entry_id)
        self.set_status(f"Saved to history as #{entry_id}")

    # ---------- Follow-up questions ----------

    def on_ask_click(self):
        if self.current_entry_id is None:
            self.set_status("Explain an error, or open one from History, first.")
            return

        question = self.question_var.get().strip()
        if not question:
            self.set_status("Type a question first.")
            return

        entry_id = self.current_entry_id
        entry = storage.get_error(entry_id)
        previous = storage.get_followups(entry_id)

        self.run_in_background(
            lambda: ask_follow_up(
                entry["error_text"],
                explanation.display_text(entry["explanation"]),
                previous,
                question,
            ),
            lambda answer, problem: self.finish_follow_up(entry_id, question, answer, problem),
        )

    def finish_follow_up(self, entry_id, question, answer, problem):
        if problem:
            self.set_status(f"Sorry, something went wrong: {problem}")
            return

        storage.save_followup(entry_id, question, answer)
        self.question_var.set("")
        if self.current_entry_id == entry_id:
            self.show_entry(entry_id)
        self.set_status("Answer added below.")

    # ---------- History actions ----------

    def on_clear_click(self):
        self.current_entry_id = None
        self.error_box.delete("1.0", "end")
        self.show_result("")
        self.question_var.set("")
        self.history_list.selection_clear(0, "end")
        self.set_status("")

    def on_history_select(self, event):
        entry_id = self.selected_entry_id()
        if entry_id is None:
            return

        entry = self.show_entry(entry_id)
        if entry is not None:
            self.set_status(f"Saved entry #{entry_id} from {entry['created_at'].replace('T', ' ')}")

    def on_delete_click(self):
        entry_id = self.selected_entry_id()
        if entry_id is None:
            messagebox.showinfo("Delete", "Select an entry in the history list first.")
            return

        if not messagebox.askyesno("Delete", f"Delete entry #{entry_id}? This can't be undone."):
            return

        storage.delete_error(entry_id)
        self.on_clear_click()
        self.refresh_history()
        self.set_status(f"Deleted entry #{entry_id}")


def main():
    root = tk.Tk()

    try:
        config.check_config()
    except SystemExit as problem:
        root.withdraw()
        messagebox.showerror("Error Explainer: setup needed", str(problem))
        root.destroy()
        return

    storage.init_db()
    ErrorExplainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
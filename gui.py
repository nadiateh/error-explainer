import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import storage


def summary_line(error_text):
    lines = error_text.strip().splitlines()
    return lines[-1] if lines else "(empty)"


class ErrorExplainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Error Explainer")
        self.root.geometry("1100x700")
        self.root.minsize(800, 500)

        self.history_ids = []

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

        ttk.Button(panel, text="Delete selected", command=self.on_delete_click).pack(fill="x", pady=(8, 0))

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
        self.result_box = ScrolledText(panel, wrap="word", state="disabled")
        self.result_box.pack(fill="both", expand=True, pady=(5, 0))

    # ---------- Small helpers ----------

    def show_result(self, text):
        self.result_box.config(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.config(state="disabled")

    def set_status(self, text):
        self.status_label.config(text=text)

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

    # ---------- Button and list actions ----------

    def on_explain_click(self):
        self.set_status("The Explain button gets connected in Step 9.")

    def on_clear_click(self):
        self.error_box.delete("1.0", "end")
        self.show_result("")
        self.history_list.selection_clear(0, "end")
        self.set_status("")

    def on_history_select(self, event):
        entry_id = self.selected_entry_id()
        if entry_id is None:
            return

        entry = storage.get_error(entry_id)
        if entry is None:
            return

        self.error_box.delete("1.0", "end")
        self.error_box.insert("1.0", entry["error_text"])
        self.show_result(entry["explanation"])
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
    storage.init_db()
    root = tk.Tk()
    ErrorExplainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
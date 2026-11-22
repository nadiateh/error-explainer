import queue
import threading
from datetime import date, datetime
from tkinter import messagebox

import customtkinter as ctk

from ai_client import explain_error, ask_follow_up, AIError
import config
import explanation
import storage
import theme
from explanation_view import ExplanationView

FOLLOW_UP_DIVIDER = "-" * 40


def split_error_line(error_text):
    lines = [line for line in error_text.strip().splitlines() if line.strip()]
    if not lines:
        return "", "(empty)"

    last = lines[-1].strip()
    name, colon, message = last.partition(":")
    if colon and name and " " not in name:
        short_name = name.split(".")[-1]
        return short_name, message.strip()
    return "", last


def is_today(created_at):
    return datetime.fromisoformat(created_at).date() == date.today()


def format_when(created_at):
    moment = datetime.fromisoformat(created_at)
    if is_today(created_at):
        return moment.strftime("%H:%M")
    return f"{moment:%b} {moment.day}"


def shorten(text, limit):
    return text if len(text) <= limit else text[: limit - 1] + "…"


class ErrorExplainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Error Explainer")
        self.root.geometry("1180x800")
        self.root.minsize(900, 600)
        self.root.configure(fg_color=theme.BG)

        ui_family, mono_family = theme.font_families()
        self.font_ui = ctk.CTkFont(family=ui_family, size=14)
        self.font_ui_small = ctk.CTkFont(family=ui_family, size=13)
        self.font_label = ctk.CTkFont(family=ui_family, size=12)
        self.font_brand = ctk.CTkFont(family=ui_family, size=16, weight="bold")
        self.font_mono = ctk.CTkFont(family=mono_family, size=13)
        self.font_mono_small = ctk.CTkFont(family=mono_family, size=12)
        self.font_mono_tiny = ctk.CTkFont(family=mono_family, size=11)

        self.results = queue.Queue()
        self.current_entry_id = None

        self.root.grid_columnconfigure(0, minsize=280)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.build_sidebar()
        self.build_main_area()

        self.refresh_history()

    # ---------- Building the window ----------

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(self.root, width=280, corner_radius=0, fg_color=theme.SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            sidebar, text="Error Explainer", font=self.font_brand, text_color=theme.TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 16))

        self.search_box = ctk.CTkEntry(
            sidebar, height=36, corner_radius=8, border_width=1,
            fg_color=theme.FIELD, border_color=theme.HAIRLINE, text_color=theme.TEXT,
            placeholder_text="Search errors and answers", placeholder_text_color=theme.MUTED,
            font=self.font_ui_small,
        )
        self.search_box.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.search_box.bind("<KeyRelease>", lambda event: self.refresh_history())

        self.history_frame = ctk.CTkScrollableFrame(
            sidebar, fg_color=theme.SIDEBAR, corner_radius=0,
            scrollbar_button_color=theme.RAISED, scrollbar_button_hover_color=theme.HAIRLINE,
        )
        self.history_frame.grid(row=2, column=0, sticky="nsew", padx=4)

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=12)
        footer.grid_columnconfigure(0, weight=1)

        self.count_label = ctk.CTkLabel(
            footer, text="", font=self.font_mono_tiny, text_color=theme.MUTED, anchor="w",
        )
        self.count_label.grid(row=0, column=0, sticky="w", padx=8)

        self.delete_button = ctk.CTkButton(
            footer, text="Delete", width=72, height=32, corner_radius=8,
            fg_color="transparent", hover_color=theme.RAISED,
            text_color=theme.TEXT_2, text_color_disabled=theme.MUTED,
            font=self.font_ui_small, command=self.on_delete_click,
        )
        self.delete_button.grid(row=0, column=1, sticky="e")

    def build_main_area(self):
        main = ctk.CTkFrame(self.root, corner_radius=0, fg_color=theme.BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(24, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="Your error", font=self.font_ui_small, text_color=theme.TEXT_2,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header, text="Paste the whole traceback, not just the last line",
            font=self.font_label, text_color=theme.MUTED,
        ).grid(row=0, column=1, sticky="e")

        self.error_box = ctk.CTkTextbox(
            main, height=150, corner_radius=12, border_width=1, border_spacing=12,
            fg_color=theme.CODE_BG, border_color=theme.HAIRLINE, text_color=theme.TEXT,
            scrollbar_button_color=theme.RAISED, font=self.font_mono, wrap="none",
        )
        self.error_box.grid(row=1, column=0, sticky="ew", padx=32)
        self.error_box.tag_config("mark", background=theme.MARK_ON_CODE, foreground=theme.MARK_TEXT)
        self.error_box.bind("<KeyRelease>", lambda event: self.highlight_error_line())
        self.error_box.bind("<Control-Return>", self.on_explain_shortcut)

        actions = ctk.CTkFrame(main, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=32, pady=(12, 24))

        self.explain_button = ctk.CTkButton(
            actions, text="Explain", width=96, height=36, corner_radius=8,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ON_ACCENT, text_color_disabled="#a8955f",
            font=ctk.CTkFont(family=self.font_ui.cget("family"), size=14, weight="bold"),
            command=self.on_explain_click,
        )
        self.explain_button.pack(side="left")

        ctk.CTkButton(
            actions, text="Clear", width=64, height=36, corner_radius=8,
            fg_color="transparent", hover_color=theme.RAISED, text_color=theme.TEXT_2,
            font=self.font_ui, command=self.on_clear_click,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            actions, text="Ctrl Enter", font=self.font_mono_tiny, text_color=theme.TEXT_2,
            fg_color=theme.RAISED, corner_radius=4, height=22,
        ).pack(side="left", padx=(12, 0))

        self.status_label = ctk.CTkLabel(
            actions, text="", font=self.font_ui_small, text_color=theme.MUTED,
        )
        self.status_label.pack(side="left", padx=(16, 0))

        card = ctk.CTkFrame(
            main, corner_radius=16, border_width=1, fg_color=theme.SURFACE, border_color=theme.HAIRLINE,
        )
        card.grid(row=3, column=0, sticky="nsew", padx=32, pady=(0, 32))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        self.result_view = ExplanationView(card)
        self.result_view.grid(row=0, column=0, sticky="nsew", padx=4, pady=(8, 0))
        self.result_view.show_welcome()

        ask_row = ctk.CTkFrame(card, fg_color="transparent")
        ask_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 16))
        ask_row.grid_columnconfigure(0, weight=1)

        self.question_box = ctk.CTkEntry(
            ask_row, height=44, corner_radius=10, border_width=1,
            fg_color=theme.BG, border_color=theme.HAIRLINE, text_color=theme.TEXT,
            placeholder_text="Ask about this error", placeholder_text_color=theme.MUTED,
            font=self.font_ui,
        )
        self.question_box.grid(row=0, column=0, sticky="ew")
        self.question_box.bind("<Return>", lambda event: self.on_ask_click())

        self.ask_button = ctk.CTkButton(
            ask_row, text="Ask", width=64, height=44, corner_radius=10,
            fg_color=theme.RAISED, hover_color=theme.HAIRLINE,
            text_color=theme.TEXT, text_color_disabled=theme.MUTED,
            font=self.font_ui, command=self.on_ask_click,
        )
        self.ask_button.grid(row=0, column=1, padx=(8, 0))

    # ---------- History list ----------

    def refresh_history(self):
        search_text = self.search_box.get().strip()
        if search_text:
            entries = storage.search_errors(search_text, limit=100)
        else:
            entries = storage.get_recent_errors(100)

        for child in self.history_frame.winfo_children():
            child.destroy()

        today = [e for e in entries if is_today(e["created_at"])]
        earlier = [e for e in entries if not is_today(e["created_at"])]

        for group_name, group in (("Today", today), ("Earlier", earlier)):
            if not group:
                continue
            ctk.CTkLabel(
                self.history_frame, text=group_name, font=self.font_label,
                text_color=theme.MUTED, anchor="w",
            ).pack(fill="x", padx=8, pady=(8, 4))
            for entry in group:
                self.build_history_row(entry)

        if not entries:
            message = "No matches" if search_text else "No saved errors yet"
            ctk.CTkLabel(
                self.history_frame, text=message, font=self.font_ui_small,
                text_color=theme.TEXT_2, anchor="w",
            ).pack(fill="x", padx=8, pady=8)

        total = storage.count_errors()
        self.count_label.configure(text=f"{total} saved")

    def build_history_row(self, entry):
        entry_id = entry["id"]
        selected = entry_id == self.current_entry_id
        error_type, message = split_error_line(entry["error_text"])

        row = ctk.CTkFrame(
            self.history_frame, corner_radius=8,
            fg_color=theme.RAISED if selected else "transparent",
        )
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=1)

        type_label = ctk.CTkLabel(
            row, text=error_type or "Error", font=self.font_mono_small, anchor="w",
            height=20, corner_radius=3,
            text_color=theme.MARK_TEXT if selected else theme.TEXT,
            fg_color=theme.MARK_ON_RAISED if selected else "transparent",
        )
        type_label.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=(8, 0))

        time_label = ctk.CTkLabel(
            row, text=format_when(entry["created_at"]), font=self.font_mono_tiny,
            text_color=theme.MUTED, height=20,
        )
        time_label.grid(row=0, column=1, sticky="e", padx=(8, 12), pady=(8, 0))

        message_label = ctk.CTkLabel(
            row, text=shorten(message, 36), font=self.font_ui_small, anchor="w", height=20,
            text_color=theme.TEXT if selected else theme.TEXT_2,
        )
        message_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(12, 12), pady=(0, 8))

        def on_enter(event):
            if not selected:
                row.configure(fg_color=theme.HOVER)

        def on_leave(event):
            if not selected:
                row.configure(fg_color="transparent")

        for widget in (row, type_label, time_label, message_label):
            widget.bind("<Button-1>", lambda event, i=entry_id: self.open_entry(i))
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    # ---------- Small helpers ----------

    def show_result(self, text):
        self.result_view.show_message(text)

    def set_status(self, text):
        self.status_label.configure(text=text)

    def set_busy(self, busy):
        new_state = "disabled" if busy else "normal"
        for button in (self.explain_button, self.ask_button, self.delete_button):
            button.configure(state=new_state)
        self.explain_button.configure(fg_color=theme.ACCENT_DISABLED if busy else theme.ACCENT)
        self.set_status("Thinking…" if busy else "")

    def highlight_error_line(self):
        self.error_box.tag_remove("mark", "1.0", "end")
        lines = self.error_box.get("1.0", "end-1c").split("\n")
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].strip():
                line_number = index + 1
                self.error_box.tag_add("mark", f"{line_number}.0", f"{line_number}.end")
                return

    def show_entry(self, entry_id, scroll_to_end=False):
        entry = storage.get_error(entry_id)
        if entry is None:
            return None

        self.current_entry_id = entry_id

        self.error_box.delete("1.0", "end")
        self.error_box.insert("1.0", entry["error_text"])
        self.highlight_error_line()

        followups = storage.get_followups(entry_id)
        self.result_view.show_entry(entry["explanation"], followups, scroll_to_end)

        return entry

    # ---------- Running AI work in the background ----------

    def run_in_background(self, task, on_done):
        def worker():
            # Runs in the background thread. No widget calls allowed in here.
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

    def on_explain_shortcut(self, event):
        self.on_explain_click()
        return "break"

    def on_explain_click(self):
        if self.explain_button.cget("state") == "disabled":
            return

        error_text = self.error_box.get("1.0", "end").strip()
        if not error_text:
            self.set_status("Paste an error first")
            return

        self.highlight_error_line()
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
            self.set_status("Not saved, this doesn't look like an error")
            return

        entry_id = storage.save_error(error_text, explanation.to_saved(data))
        self.show_entry(entry_id)
        self.refresh_history()
        self.set_status(f"Saved as #{entry_id}")

    # ---------- Follow-up questions ----------

    def on_ask_click(self):
        if self.ask_button.cget("state") == "disabled":
            return

        if self.current_entry_id is None:
            self.set_status("Explain an error, or open one from History, first")
            return

        question = self.question_box.get().strip()
        if not question:
            self.set_status("Type a question first")
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
        self.question_box.delete(0, "end")
        if self.current_entry_id == entry_id:
            self.show_entry(entry_id, scroll_to_end=True)
        self.set_status("Answer added")

    # ---------- History actions ----------

    def open_entry(self, entry_id):
        entry = self.show_entry(entry_id)
        if entry is None:
            return
        self.refresh_history()
        self.set_status(f"Saved {format_when(entry['created_at'])}")

    def on_clear_click(self):
        self.current_entry_id = None
        self.error_box.delete("1.0", "end")
        self.result_view.show_welcome()
        self.question_box.delete(0, "end")
        self.set_status("")
        self.refresh_history()

    def on_delete_click(self):
        entry_id = self.current_entry_id
        if entry_id is None:
            messagebox.showinfo("Delete", "Open an entry from History first.")
            return

        if not messagebox.askyesno("Delete", f"Delete entry #{entry_id}? This can't be undone."):
            return

        storage.delete_error(entry_id)
        self.on_clear_click()
        self.set_status(f"Deleted #{entry_id}")


def main():
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()

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
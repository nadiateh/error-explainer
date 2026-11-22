import tkinter as tk

import customtkinter as ctk

import explanation
import theme

PAD = 24


class ExplanationView(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(
            master, fg_color=theme.SURFACE, corner_radius=0,
            scrollbar_button_color=theme.RAISED, scrollbar_button_hover_color=theme.HAIRLINE,
        )
        self.grid_columnconfigure(0, weight=1)

        ui, mono = theme.font_families()
        self.font_summary = ctk.CTkFont(family=ui, size=20)
        self.font_body = ctk.CTkFont(family=ui, size=14)
        self.font_details = ctk.CTkFont(family=ui, size=15)
        self.font_heading = ctk.CTkFont(family=ui, size=13)
        self.font_mono = ctk.CTkFont(family=mono, size=13)
        self.font_mono_small = ctk.CTkFont(family=mono, size=12)

        self.width = 640
        self.wrapped = []
        self.bind("<Configure>", self.on_resize, add="+")

    # ---------- Keeping text wrapped to the card's width ----------

    def on_resize(self, event):
        self.width = event.width
        for label, indent in self.wrapped:
            label.configure(wraplength=max(160, self.width - indent))

    def text(self, parent, words, font, color, indent, **label_options):
        label = ctk.CTkLabel(
            parent, text=words, font=font, text_color=color,
            anchor="w", justify="left", wraplength=max(160, self.width - indent),
            **label_options,
        )
        self.wrapped.append((label, indent))
        return label

    def clear(self):
        for child in self.winfo_children():
            child.destroy()
        self.wrapped = []

    def scroll_to(self, position):
        self.update_idletasks()
        self._parent_canvas.yview_moveto(position)

    # ---------- Small building blocks ----------

    def section(self, background="transparent"):
        frame = ctk.CTkFrame(self, fg_color=background, corner_radius=0)
        frame.pack(fill="x")
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def hairline(self):
        tk.Frame(self, height=1, bg=theme.HAIRLINE).pack(fill="x")

    def heading(self, parent, words):
        ctk.CTkLabel(
            parent, text=words, font=self.font_heading, text_color=theme.TEXT_2, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(20, 8))

    def code_block(self, parent, code):
        line_count = len(code.splitlines()) or 1
        line_height = self.font_mono.metrics("linespace")
        box = ctk.CTkTextbox(
            parent, height=line_count * line_height + 24, corner_radius=8,
            border_width=1, border_spacing=8, wrap="none",
            fg_color=theme.CODE_BG, border_color=theme.HAIRLINE, text_color=theme.TEXT,
            scrollbar_button_color=theme.RAISED, font=self.font_mono,
        )
        box.insert("1.0", code)
        box.configure(state="disabled")
        return box

    # ---------- What the card can show ----------

    def show_message(self, words):
        self.clear()
        self.text(self, words, self.font_body, theme.TEXT_2, indent=2 * PAD).pack(
            fill="x", padx=PAD, pady=PAD,
        )
        self.scroll_to(0)

    def show_welcome(self):
        self.clear()

        intro = self.section()
        ctk.CTkLabel(
            intro, text="Read an error from the bottom up", font=self.font_summary,
            text_color=theme.TEXT, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(PAD, 4))
        self.text(
            intro,
            "The last line says what went wrong. The lines above it say where. "
            "Paste all of it and you'll get both explained",
            self.font_body, theme.TEXT_2, indent=2 * PAD,
        ).pack(fill="x", padx=PAD, pady=(0, 20))

        sample = ctk.CTkFrame(intro, fg_color="transparent")
        sample.pack(fill="x", padx=PAD, pady=(0, PAD))
        sample.grid_columnconfigure(0, weight=1)

        rows = [
            ("Traceback (most recent call last):", theme.MUTED, "The trail Python followed", theme.MUTED),
            ('  File "app.py", line 3, in <module>', theme.TEXT_2, "Where it happened", theme.TEXT_2),
            ("    print(total + 5)", theme.TEXT, "The line that failed", theme.TEXT_2),
            ("NameError: name 'total' is not defined", None, "What went wrong. Start here", theme.MARK_TEXT),
        ]
        for row_number, (code, code_color, note, note_color) in enumerate(rows):
            is_last = row_number == len(rows) - 1
            line = ctk.CTkFrame(sample, fg_color=theme.CODE_BG, corner_radius=0)
            line.grid(row=row_number, column=0, sticky="nsew")
            ctk.CTkLabel(
                line, text=code, font=self.font_mono, anchor="w", height=26, corner_radius=3,
                text_color=theme.MARK_TEXT if is_last else code_color,
                fg_color=theme.MARK_ON_CODE if is_last else "transparent",
            ).pack(anchor="w", padx=12, pady=(10 if row_number == 0 else 0, 10 if is_last else 0))
            ctk.CTkLabel(
                sample, text=note, font=self.font_heading, text_color=note_color, anchor="w", height=26,
            ).grid(row=row_number, column=1, sticky="w", padx=(20, 0))

        self.scroll_to(0)

    def show_entry(self, saved_explanation, followups, scroll_to_end=False):
        self.clear()

        data = explanation.load(saved_explanation)
        if data is None:
            self.text(self, saved_explanation, self.font_body, theme.TEXT, indent=2 * PAD).pack(
                fill="x", padx=PAD, pady=PAD,
            )
        else:
            self.build_card(data)

        if followups:
            self.build_followups(followups)

        self.scroll_to(1 if scroll_to_end else 0)

    # ---------- The structured explanation ----------

    def build_card(self, data):
        top = self.section()
        tags = ctk.CTkFrame(top, fg_color="transparent")
        tags.pack(fill="x", padx=PAD, pady=(PAD, 12))
        ctk.CTkLabel(
            tags, text=f" {data['error_type'] or 'Error'} ", font=self.font_mono,
            text_color=theme.MARK_TEXT, fg_color=theme.MARK_ON_SURFACE, corner_radius=4, height=24,
        ).pack(side="left")
        if data["location"]:
            ctk.CTkLabel(
                tags, text=data["location"], font=self.font_mono_small, text_color=theme.MUTED,
            ).pack(side="left", padx=(12, 0))

        self.text(top, data["summary"], self.font_summary, theme.TEXT, indent=2 * PAD).pack(
            fill="x", padx=PAD,
        )
        self.text(top, data["details"], self.font_details, theme.TEXT_2, indent=2 * PAD).pack(
            fill="x", padx=PAD, pady=(8, 20),
        )

        if data["causes"]:
            self.hairline()
            causes = self.section()
            self.heading(causes, "Likely causes")
            for number, cause in enumerate(data["causes"], start=1):
                self.build_cause(causes, number, cause)
            ctk.CTkFrame(causes, height=12, fg_color="transparent").pack()

        if data["steps"]:
            self.hairline()
            steps = self.section()
            self.heading(steps, "Debugging steps")
            for number, step in enumerate(data["steps"], start=1):
                self.build_step(steps, number, step)
            ctk.CTkFrame(steps, height=8, fg_color="transparent").pack()

        if data["prevention"]:
            self.hairline()
            strip = self.section(background=theme.STRIP)
            strip.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                strip, text="Next time", font=self.font_heading, text_color=theme.TEXT_2,
            ).grid(row=0, column=0, sticky="nw", padx=(PAD, 12), pady=16)
            self.text(
                strip, data["prevention"], self.font_body, theme.TEXT, indent=2 * PAD + 92,
            ).grid(row=0, column=1, sticky="ew", padx=(0, PAD), pady=16)

    def build_cause(self, parent, number, cause):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD, pady=4)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row, text=str(number), font=self.font_mono_small, text_color=theme.MUTED, width=16, anchor="w",
        ).grid(row=0, column=0, sticky="nw", padx=(0, 12))

        words = ctk.CTkFrame(row, fg_color="transparent")
        words.grid(row=0, column=1, sticky="ew")
        if number == 1:
            ctk.CTkLabel(
                words, text=" Most likely ", font=self.font_heading, height=22, corner_radius=3,
                text_color=theme.MARK_TEXT, fg_color=theme.MARK_ON_SURFACE,
            ).pack(anchor="w", pady=(0, 4))
        self.text(
            words, cause, self.font_body, theme.TEXT if number == 1 else theme.TEXT_2,
            indent=2 * PAD + 28,
        ).pack(fill="x")

    def build_step(self, parent, number, step):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD, pady=8)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row, text=str(number), font=self.font_mono_small, text_color=theme.TEXT,
            width=24, height=24, corner_radius=6, fg_color=theme.RAISED,
        ).grid(row=0, column=0, sticky="nw", padx=(0, 12))

        body = ctk.CTkFrame(row, fg_color="transparent")
        body.grid(row=0, column=1, sticky="ew")
        self.text(body, step["text"], self.font_body, theme.TEXT, indent=2 * PAD + 36).pack(fill="x")
        if step["code"]:
            self.code_block(body, step["code"]).pack(fill="x", pady=(8, 0))

    # ---------- Follow-up conversation ----------

    def build_followups(self, followups):
        self.hairline()
        talk = self.section()
        for item in followups:
            question_row = ctk.CTkFrame(talk, fg_color="transparent")
            question_row.pack(fill="x", padx=PAD, pady=(20, 8))
            bubble = ctk.CTkLabel(
                question_row, text=item["question"], font=self.font_body, text_color=theme.TEXT,
                fg_color=theme.BUBBLE, corner_radius=12, anchor="w", justify="left",
                wraplength=max(160, int(self.width * 0.6)),
            )
            bubble.pack(side="right", ipadx=10, ipady=6)

            self.text(talk, item["answer"], self.font_body, theme.TEXT_2, indent=2 * PAD).pack(
                fill="x", padx=PAD,
            )
        ctk.CTkFrame(talk, height=20, fg_color="transparent").pack()
import tkinter as tk


class LineNumbers(tk.Canvas):
    """A line-number gutter that mirrors a tk.Text widget."""

    def __init__(self, master, text_widget: tk.Text, **kwargs):
        kwargs.setdefault("width", 40)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("borderwidth", 0)
        kwargs.setdefault("background", "#f0f0f0")
        super().__init__(master, **kwargs)
        self.text = text_widget
        self.text.bind("<<Modified>>", self._on_modified, add="+")
        self.text.bind("<Configure>", self._redraw, add="+")
        self.text.bind("<KeyRelease>", self._redraw, add="+")
        self.text.bind("<MouseWheel>", lambda e: self.after_idle(self._redraw), add="+")
        self.text.bind("<Button-4>", lambda e: self.after_idle(self._redraw), add="+")
        self.text.bind("<Button-5>", lambda e: self.after_idle(self._redraw), add="+")
        self._wrap_yview()
        self.bind("<Configure>", self._redraw)

    def _wrap_yview(self):
        original = self.text.yview

        def wrapped(*args, **kwargs):
            result = original(*args, **kwargs)
            self.after_idle(self._redraw)
            return result

        self.text.yview = wrapped

    def _on_modified(self, _event=None):
        self._redraw()
        try:
            self.text.edit_modified(False)
        except tk.TclError:
            pass

    def redraw(self):
        self._redraw()

    def _redraw(self, _event=None):
        self.delete("all")
        try:
            i = self.text.index("@0,0")
        except tk.TclError:
            return
        font = self.text.cget("font")
        while True:
            dline = self.text.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_num = str(i).split(".")[0]
            self.create_text(
                int(self.cget("width")) - 4,
                y,
                anchor="ne",
                text=line_num,
                font=font,
                fill="#888888",
            )
            i = self.text.index(f"{i}+1line")

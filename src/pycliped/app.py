import time
import traceback
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import pyperclip

from . import config as cfg_mod
from .linenumbers import LineNumbers
from .presets import DEFAULT_PRESET, PRESETS
from .runner import compile_user_code, run_user_code

HISTORY_LIMIT = 20
MIN_POLL_MS = 100
MAX_POLL_MS = 5000


class CollapsibleFrame(ttk.Frame):
    """A simple show/hide frame toggled by a button."""

    def __init__(self, master, text: str, expanded: bool = False, on_toggle=None):
        super().__init__(master)
        self._title = text
        self._expanded = expanded
        self._on_toggle = on_toggle
        self._toggle_btn = ttk.Button(
            self, text=self._label(), command=self._toggle, style="Toolbutton"
        )
        self._toggle_btn.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.body = ttk.Frame(self)
        if expanded:
            self.body.grid(row=1, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def _label(self) -> str:
        arrow = "▾" if self._expanded else "▸"
        return f"{arrow} {self._title}"

    def _toggle(self):
        self._expanded = not self._expanded
        self._toggle_btn.config(text=self._label())
        if self._expanded:
            self.body.grid(row=1, column=0, sticky="nsew")
        else:
            self.body.grid_remove()
        if self._on_toggle:
            self._on_toggle(self._expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool):
        if expanded != self._expanded:
            self._toggle()


class PycliApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("pycliped")

        self.cfg = cfg_mod.load()

        self.last_seen: str = ""
        self.last_written: str | None = None
        self.original_text: str = ""
        self.current_func = None
        self.compile_error: Exception | None = None
        self.code_dirty = False
        self.history: list[dict] = list(self.cfg.get("history") or [])
        self._after_id: str | None = None
        self._suppress_dirty = False

        self._build_ui()
        self._restore_state()
        self._compile_current_code()
        self._populate_history_list()
        self._schedule_tick()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI construction ----------

    def _build_ui(self):
        mono = tkfont.nametofont("TkFixedFont")

        # Top control bar
        top = ttk.Frame(self.root)
        top.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        top.columnconfigure(2, weight=1)

        self.enabled_var = tk.BooleanVar(value=True)
        self.enabled_chk = ttk.Checkbutton(
            top,
            text="Enabled",
            variable=self.enabled_var,
            command=self._on_enabled_toggle,
        )
        self.enabled_chk.grid(row=0, column=0, padx=(0, 12))

        ttk.Label(top, text="Preset:").grid(row=0, column=2, sticky="e", padx=(0, 4))
        self.preset_var = tk.StringVar(value=DEFAULT_PRESET)
        self.preset_combo = ttk.Combobox(
            top,
            state="readonly",
            textvariable=self.preset_var,
            values=list(PRESETS.keys()),
            width=32,
        )
        self.preset_combo.grid(row=0, column=3, padx=(0, 12))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        ttk.Label(top, text="Poll (ms):").grid(row=0, column=4, padx=(0, 4))
        self.poll_var = tk.IntVar(value=500)
        self.poll_spin = ttk.Spinbox(
            top,
            from_=MIN_POLL_MS,
            to=MAX_POLL_MS,
            increment=100,
            textvariable=self.poll_var,
            width=6,
            command=self._on_poll_change,
        )
        self.poll_spin.grid(row=0, column=5)
        self.poll_spin.bind("<FocusOut>", lambda _e: self._on_poll_change())
        self.poll_spin.bind("<Return>", lambda _e: self._on_poll_change())

        # Code editor
        editor_frame = ttk.LabelFrame(
            self.root,
            text="Python (function body — argument is `text`; use `return` to set new clipboard)",
        )
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=2)
        editor_frame.columnconfigure(1, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        self.code_text = tk.Text(
            editor_frame, height=14, wrap="none", font=mono, undo=True
        )
        self.code_lines = LineNumbers(editor_frame, self.code_text, width=40)
        code_scroll_y = ttk.Scrollbar(
            editor_frame, orient="vertical", command=self.code_text.yview
        )
        code_scroll_x = ttk.Scrollbar(
            editor_frame, orient="horizontal", command=self.code_text.xview
        )
        self.code_text.configure(
            yscrollcommand=code_scroll_y.set, xscrollcommand=code_scroll_x.set
        )

        self.code_lines.grid(row=0, column=0, sticky="ns")
        self.code_text.grid(row=0, column=1, sticky="nsew")
        code_scroll_y.grid(row=0, column=2, sticky="ns")
        code_scroll_x.grid(row=1, column=1, sticky="ew")
        self.code_text.bind("<<Modified>>", self._on_code_modified, add="+")

        # Run-now bar (just below the code editor)
        run_bar = ttk.Frame(self.root)
        run_bar.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 4))
        self.run_now_btn = ttk.Button(
            run_bar,
            text="Run on clipboard contents now",
            command=self._run_now,
        )
        self.run_now_btn.grid(row=0, column=0, sticky="w")

        # Preview (collapsible)
        self.preview_section = CollapsibleFrame(
            self.root, "Preview (original / result)", expanded=False
        )
        self.preview_section.grid(row=3, column=0, sticky="nsew", padx=6, pady=2)
        preview_paned = ttk.PanedWindow(
            self.preview_section.body, orient="horizontal"
        )
        preview_paned.grid(row=0, column=0, sticky="nsew")
        self.preview_section.body.columnconfigure(0, weight=1)
        self.preview_section.body.rowconfigure(0, weight=1)

        self.original_text_widget = self._make_preview_pane(
            preview_paned, "Original clipboard"
        )
        self.result_text_widget = self._make_preview_pane(
            preview_paned, "Result (returned text)"
        )
        preview_paned.add(self.original_text_widget.master, weight=1)
        preview_paned.add(self.result_text_widget.master, weight=1)

        # History (collapsible)
        self.history_section = CollapsibleFrame(
            self.root, "History (recent transformations)", expanded=False
        )
        self.history_section.grid(row=4, column=0, sticky="nsew", padx=6, pady=2)
        self.history_listbox = tk.Listbox(self.history_section.body, height=6)
        history_scroll = ttk.Scrollbar(
            self.history_section.body,
            orient="vertical",
            command=self.history_listbox.yview,
        )
        self.history_listbox.configure(yscrollcommand=history_scroll.set)
        self.history_listbox.grid(row=0, column=0, sticky="nsew")
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.history_section.body.columnconfigure(0, weight=1)
        self.history_section.body.rowconfigure(0, weight=1)
        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)

        # Status bar
        self.status_var = tk.StringVar(value="")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            relief="sunken",
            padding=(6, 2),
        )
        status_bar.grid(row=5, column=0, sticky="ew")

        # Layout weights — code editor expands the most.
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=3)
        self.root.rowconfigure(3, weight=2)
        self.root.rowconfigure(4, weight=1)

    def _make_preview_pane(self, parent, label: str) -> tk.Text:
        mono = tkfont.nametofont("TkFixedFont")
        wrapper = ttk.Frame(parent)
        ttk.Label(wrapper, text=label).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=2
        )
        text = tk.Text(wrapper, height=6, wrap="none", font=mono)
        text.configure(state="disabled")
        line_nums = LineNumbers(wrapper, text, width=40)
        scroll_y = ttk.Scrollbar(wrapper, orient="vertical", command=text.yview)
        scroll_x = ttk.Scrollbar(wrapper, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        line_nums.grid(row=1, column=0, sticky="ns")
        text.grid(row=1, column=1, sticky="nsew")
        scroll_y.grid(row=1, column=2, sticky="ns")
        scroll_x.grid(row=2, column=1, sticky="ew")
        wrapper.columnconfigure(1, weight=1)
        wrapper.rowconfigure(1, weight=1)
        return text

    # ---------- State / persistence ----------

    def _restore_state(self):
        self.enabled_var.set(bool(self.cfg.get("enabled", True)))
        preset_name = self.cfg.get("preset") or DEFAULT_PRESET
        if preset_name not in PRESETS:
            preset_name = DEFAULT_PRESET
        self.preset_var.set(preset_name)
        self.poll_var.set(int(self.cfg.get("poll_interval_ms", 500) or 500))
        code = self.cfg.get("code") or PRESETS[preset_name]
        self._set_code(code)
        self.code_dirty = False
        geom = self.cfg.get("geometry")
        if geom:
            try:
                self.root.geometry(geom)
            except tk.TclError:
                pass
        self.preview_section.set_expanded(bool(self.cfg.get("preview_visible")))
        self.history_section.set_expanded(bool(self.cfg.get("history_visible")))

    def _gather_state(self) -> dict:
        return {
            "enabled": bool(self.enabled_var.get()),
            "preset": self.preset_var.get(),
            "code": self.code_text.get("1.0", "end-1c"),
            "poll_interval_ms": int(self._clamped_poll()),
            "geometry": self.root.geometry(),
            "preview_visible": self.preview_section.is_expanded(),
            "history_visible": self.history_section.is_expanded(),
            "history": self.history[-HISTORY_LIMIT:],
        }

    def _on_close(self):
        try:
            cfg_mod.save(self._gather_state())
        finally:
            if self._after_id:
                try:
                    self.root.after_cancel(self._after_id)
                except tk.TclError:
                    pass
            self.root.destroy()

    # ---------- Editor helpers ----------

    def _set_code(self, code: str):
        self._suppress_dirty = True
        self.code_text.configure(state="normal")
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", code)
        self.code_text.edit_modified(False)
        self._suppress_dirty = False
        self.code_dirty = False
        self.code_lines.redraw()

    def _on_code_modified(self, _event=None):
        if self._suppress_dirty:
            try:
                self.code_text.edit_modified(False)
            except tk.TclError:
                pass
            return
        try:
            modified = self.code_text.edit_modified()
        except tk.TclError:
            modified = False
        if modified:
            self.code_dirty = True
            self.compile_error = None
            try:
                self.code_text.edit_modified(False)
            except tk.TclError:
                pass

    def _compile_current_code(self) -> bool:
        body = self.code_text.get("1.0", "end-1c")
        try:
            self.current_func = compile_user_code(body)
            self.compile_error = None
            self.code_dirty = False
            return True
        except Exception as e:
            self.current_func = None
            self.compile_error = e
            self._set_status(f"Compile error: {type(e).__name__}: {e}")
            self._set_preview_result(traceback.format_exc())
            return False

    # ---------- Enabled toggle ----------

    def _on_enabled_toggle(self):
        if not self.enabled_var.get():
            self._set_status("Disabled currently")
        else:
            self._set_status("")

    # ---------- Preset / poll handlers ----------

    def _on_preset_change(self, _event=None):
        name = self.preset_var.get()
        if name not in PRESETS:
            return
        if self.code_dirty:
            keep = messagebox.askyesno(
                "Discard custom code?",
                "The code editor has unsaved changes. Replace them with the "
                f"'{name}' preset?",
                parent=self.root,
            )
            if not keep:
                # revert dropdown selection visually
                # Best effort: leave var as-is; user can re-pick.
                return
        self._set_code(PRESETS[name])
        if self._compile_current_code():
            # Immediately apply the new preset to the *original* clipboard text,
            # not the previously-transformed result, so users can compare presets.
            if self.original_text:
                self._apply(
                    self.original_text,
                    update_clipboard=self.enabled_var.get(),
                    label=f"Preset '{name}' applied",
                )

    def _clamped_poll(self) -> int:
        try:
            v = int(self.poll_var.get())
        except (tk.TclError, ValueError):
            v = 500
        return max(MIN_POLL_MS, min(MAX_POLL_MS, v))

    def _on_poll_change(self):
        self.poll_var.set(self._clamped_poll())
        # Reschedule the next tick at the new cadence.
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self._schedule_tick()

    # ---------- Polling / transform pipeline ----------

    def _schedule_tick(self):
        self._after_id = self.root.after(self._clamped_poll(), self._tick)

    def _tick(self):
        self._after_id = None
        try:
            current = pyperclip.paste()
        except Exception as e:
            self._set_status(f"Clipboard error: {type(e).__name__}: {e}")
            self._schedule_tick()
            return

        if not isinstance(current, str):
            self._schedule_tick()
            return

        if current == self.last_seen:
            self._schedule_tick()
            return

        self.last_seen = current

        if current == self.last_written:
            # This change was caused by us writing — skip.
            self._schedule_tick()
            return

        if not self.enabled_var.get():
            self._schedule_tick()
            return

        if current.strip() == "":
            self._schedule_tick()
            return

        self._apply(current, update_clipboard=True, label="Clipboard updated")
        self._schedule_tick()

    def _run_now(self):
        try:
            current = pyperclip.paste()
        except Exception as e:
            self._set_status(f"Clipboard error: {type(e).__name__}: {e}")
            return
        if not isinstance(current, str) or current == "":
            self._set_status("Clipboard is empty or non-text — nothing to run.")
            return
        self._apply(
            current, update_clipboard=self.enabled_var.get(), label="Run now"
        )

    def _apply(self, source_text: str, update_clipboard: bool, label: str):
        """Run user code against ``source_text`` and update preview/clipboard.

        ``source_text`` is the input — typically the most-recent clipboard
        contents seen by the app. The Result preview, history, and status bar
        are always updated. Clipboard is only written when ``update_clipboard``
        is True and the result actually differs from the source.
        """
        # Always recompile if dirty or never compiled.
        if self.current_func is None or self.code_dirty:
            if not self._compile_current_code():
                return

        self.original_text = source_text
        self._set_preview_original(source_text)

        try:
            result = run_user_code(self.current_func, source_text)
        except Exception:
            tb = traceback.format_exc()
            self._set_preview_result(tb)
            # Status bar gets only the last non-empty line of the traceback.
            last_line = next(
                (l for l in reversed(tb.splitlines()) if l.strip()),
                "Error",
            )
            self._set_status(f"Error: {last_line}")
            return

        if result is None:
            self._set_preview_result("(user code returned None — clipboard unchanged)")
            self._set_status(f"{label}: no return value at {self._timestamp()}")
            return

        self._set_preview_result(result)

        if update_clipboard and result != source_text:
            try:
                pyperclip.copy(result)
                self.last_written = result
                self.last_seen = result
            except Exception as e:
                self._set_status(f"Clipboard write error: {type(e).__name__}: {e}")
                return
            self._set_status(f"{label} {self._timestamp()}")
        elif result == source_text:
            self._set_status(f"{label}: no change at {self._timestamp()}")
        else:
            # update_clipboard False (e.g. disabled while previewing presets)
            self._set_status(f"{label}: preview only at {self._timestamp()}")

        self._add_history(source_text, result)

    # ---------- Preview / status / history ----------

    def _set_preview_original(self, text: str):
        self._write_readonly(self.original_text_widget, text)

    def _set_preview_result(self, text: str):
        self._write_readonly(self.result_text_widget, text)

    @staticmethod
    def _write_readonly(widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _set_status(self, text: str):
        self.status_var.set(text)

    @staticmethod
    def _timestamp() -> str:
        now = time.time()
        local = time.localtime(now)
        tenths = int((now - int(now)) * 10)
        return (
            time.strftime("%I:%M:%S", local)
            + f".{tenths} "
            + time.strftime("%p %Y/%m/%d", local)
        )

    def _add_history(self, original: str, result: str):
        entry = {
            "ts": time.strftime("%H:%M:%S"),
            "original": original,
            "result": result,
        }
        self.history.append(entry)
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]
        self._populate_history_list()

    def _populate_history_list(self):
        self.history_listbox.delete(0, "end")
        for entry in self.history:
            orig = entry.get("original", "").splitlines()
            res = entry.get("result", "").splitlines()
            orig_preview = (orig[0] if orig else "")[:40]
            res_preview = (res[0] if res else "")[:40]
            ts = entry.get("ts", "")
            self.history_listbox.insert(
                "end", f"{ts}  {orig_preview}  →  {res_preview}"
            )

    def _on_history_select(self, _event=None):
        sel = self.history_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i >= len(self.history):
            return
        entry = self.history[i]
        self._set_preview_original(entry.get("original", ""))
        self._set_preview_result(entry.get("result", ""))
        self.preview_section.set_expanded(True)


def main():
    root = tk.Tk()
    PycliApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

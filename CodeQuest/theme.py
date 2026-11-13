import random
import tkinter as tk

from constants import *

_SYMBOLS = ["{}", "<>", "();", "=>", "[]", "//", "#", "λ", "01", "</>", "fn", "::", "&&", "++"]


def widget_bg(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return BG


def round_rect(canvas, x1, y1, x2, y2, r=18, **kwargs):
    r = max(0, min(r, abs(x2 - x1) / 2, abs(y2 - y1) / 2))
    return canvas.create_polygon(
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
        smooth=True,
        **kwargs,
    )


def _btn_pixels(width, height):
    px_w = int(width) * 10 + 48
    px_h = 44 if height <= 1 else 58
    return max(px_w, 112), max(px_h, 40)


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        bg=PRIMARY,
        fg=WHITE,
        hover=GLOW_BLUE,
        width=18,
        height=2,
        font=(FONT, 13, "bold"),
        radius=18,
    ):
        pbg = widget_bg(parent)
        px_w, px_h = _btn_pixels(width, height)
        super().__init__(
            parent,
            width=px_w,
            height=px_h,
            bg=pbg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=0,
        )
        self.command = command
        self._bg = bg
        self._fg = fg
        self._hover = hover
        self._radius = radius
        self._px_w = px_w
        self._px_h = px_h
        self._font = font
        self._text = text
        self._pbg = pbg
        self._glow = None
        self._shape = None
        self._label = None
        self._hovering = False
        self._pressed = False
        self._draw(bg, pbg, fg)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._lock_size)

    def _lock_size(self, event):
        try:
            if not self.winfo_exists():
                return
            if event.width != self._px_w or event.height != self._px_h:
                self.configure(width=self._px_w, height=self._px_h)
        except tk.TclError:
            return

    def _draw(self, fill, glow, text_color):
        self.delete("all")
        self._glow = round_rect(
            self,
            1,
            1,
            self._px_w - 1,
            self._px_h - 1,
            self._radius + 2,
            fill=glow,
            outline=glow,
            width=1,
        )
        self._shape = round_rect(
            self,
            4,
            4,
            self._px_w - 4,
            self._px_h - 4,
            self._radius,
            fill=fill,
            outline=fill,
            width=1,
        )
        self._label = self.create_text(
            self._px_w / 2,
            self._px_h / 2,
            text=self._text,
            fill=text_color,
            font=self._font,
        )

    def _paint(self):
        if not self._shape:
            return
        fill = self._hover if self._hovering else self._bg
        glow = self._hover if self._hovering else self._pbg
        if self._pressed:
            fill = self._bg
        self.itemconfigure(self._glow, fill=glow, outline=glow)
        self.itemconfigure(self._shape, fill=fill, outline=fill)
        self.itemconfigure(self._label, fill=GOLD if self._pressed else self._fg)

    def _on_enter(self, _e):
        self._hovering = True
        self._paint()

    def _on_leave(self, _e):
        self._hovering = False
        self._pressed = False
        self._paint()

    def _on_press(self, _e):
        self._pressed = True
        self._paint()

    def _on_release(self, event):
        self._pressed = False
        self._paint()
        if 0 <= event.x <= self._px_w and 0 <= event.y <= self._px_h and self.command:
            self.command()


def styled_button(
    parent,
    text,
    command,
    bg=PRIMARY,
    fg=WHITE,
    hover=GLOW_BLUE,
    width=18,
    height=2,
    font=(FONT, 13, "bold"),
):
    return RoundedButton(
        parent,
        text,
        command,
        bg=bg,
        fg=fg,
        hover=hover,
        width=width,
        height=height,
        font=font,
    )


class GlassCard(tk.Frame):
    def __init__(self, parent, padx=18, pady=18, radius=22, width=None):
        pbg = widget_bg(parent)
        super().__init__(parent, bg=pbg, highlightthickness=0, bd=0)
        self._padx = padx
        self._pady = pady
        self._radius = radius
        self._pbg = pbg
        self.canvas = tk.Canvas(self, bg=pbg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=CARD)
        self._window = self.canvas.create_window(padx, pady, anchor="nw", window=self.inner)
        self.inner.bind("<Configure>", self._redraw)
        if width:
            self.configure(width=width)

    def destroy(self):
        try:
            self.inner.unbind("<Configure>")
        except tk.TclError:
            pass
        try:
            if getattr(self, "_window", None) is not None:
                self.canvas.delete(self._window)
                self._window = None
        except tk.TclError:
            pass
        try:
            if self.inner.winfo_exists():
                self.inner.destroy()
        except tk.TclError:
            pass
        try:
            super().destroy()
        except tk.TclError:
            pass

    def _redraw(self, _e=None):
        try:
            if not self.winfo_exists() or not self.inner.winfo_exists():
                return
            req_w = max(self.inner.winfo_reqwidth() + self._padx * 2, 80)
            req_h = max(self.inner.winfo_reqheight() + self._pady * 2, 60)
            self.canvas.configure(width=req_w, height=req_h)
            self.canvas.delete("shape")
            round_rect(
                self.canvas,
                1,
                1,
                req_w - 1,
                req_h - 1,
                self._radius + 2,
                fill=SHADOW,
                outline=SHADOW,
                width=1,
                tags="shape",
            )
            round_rect(
                self.canvas,
                4,
                4,
                req_w - 4,
                req_h - 4,
                self._radius,
                fill=CARD,
                outline=GLASS_LINE,
                width=1,
                tags="shape",
            )
            self.canvas.tag_lower("shape")
            self.canvas.coords(self._window, self._padx, self._pady)
        except tk.TclError:
            return


def glass_card(parent, width=None, padx=18, pady=18):
    panel = GlassCard(parent, padx=padx, pady=pady, width=width)
    return panel, panel.inner


def section_title(parent, text, color=WHITE, size=22, bg=None):
    return tk.Label(
        parent,
        text=text,
        font=(FONT, size, "bold"),
        fg=color,
        bg=bg or widget_bg(parent),
    )


def muted_label(parent, text, size=12, bg=None, fg=MUTED):
    return tk.Label(
        parent,
        text=text,
        font=(FONT, size),
        fg=fg,
        bg=bg or widget_bg(parent),
    )


def kbd_key(parent, text, bg=None):
    key = tk.Frame(
        parent,
        bg=SECONDARY,
        highlightbackground=GLASS_LINE,
        highlightthickness=2,
        bd=0,
    )
    tk.Label(
        key,
        text=text,
        font=(FONT_MONO, 10, "bold"),
        fg=WHITE,
        bg=SECONDARY,
        padx=8,
        pady=3,
    ).pack()
    return key


def stat_chip(parent, value, label, value_fg=WHITE):
    cell = tk.Frame(
        parent,
        bg=SECONDARY,
        highlightbackground=GLASS_LINE,
        highlightthickness=2,
        bd=0,
    )
    tk.Label(cell, text=value, font=(FONT, 16, "bold"), fg=value_fg, bg=SECONDARY).pack(pady=(12, 0), padx=18)
    tk.Label(cell, text=label, font=(FONT, 10), fg=MUTED, bg=SECONDARY).pack(pady=(0, 12), padx=18)
    return cell


def header_chip(parent, text, fg=WHITE, bg=CARD2):
    chip = tk.Frame(parent, bg=bg, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
    tk.Label(chip, text=text, font=(FONT, 11, "bold"), fg=fg, bg=bg, padx=12, pady=6).pack()
    return chip


def info_row(parent, label, value, bg=SECONDARY):
    row = tk.Frame(parent, bg=bg, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
    tk.Label(row, text=label, font=(FONT, 11), fg=MUTED, bg=bg, width=16, anchor="w").pack(
        side="left", padx=12, pady=10
    )
    tk.Label(row, text=value, font=(FONT, 13, "bold"), fg=WHITE, bg=bg).pack(side="left")
    return row


def progress_track(parent, bg=CARD2, fill=PRIMARY, height=10):
    track = tk.Frame(parent, bg=bg, height=height, highlightthickness=0, bd=0)
    bar = tk.Frame(track, bg=fill, height=height)
    bar.place(relx=0, rely=0, relwidth=0.02, relheight=1)
    return track, bar


def animate_bar(bar, target, jobs, step=1, delay=16, increment=0.03):
    def grow(n=1):
        try:
            if not bar.winfo_exists():
                return
            width = min(target, increment * n)
            bar.place(relwidth=width)
            if increment * n < target:
                jobs.append(bar.after(delay, grow, n + 1))
        except tk.TclError:
            return

    grow()


class ParticleCanvas(tk.Canvas):
    def __init__(self, master, jobs):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0)
        self.jobs = jobs
        self.particles = []
        self._alive = True
        self.bind("<Configure>", self._on_configure)

    def shutdown(self):
        self._alive = False
        try:
            self.unbind("<Configure>")
        except tk.TclError:
            pass

    def destroy(self):
        self.shutdown()
        try:
            super().destroy()
        except tk.TclError:
            pass

    def _on_configure(self, _e=None):
        if self._alive and not self.particles:
            self._spawn()

    def _spawn(self):
        self.delete("particle")
        self.particles = []
        w = max(self.winfo_width(), 800)
        h = max(self.winfo_height(), 600)
        for _ in range(40):
            x = random.randint(20, max(40, w - 20))
            y = random.randint(20, max(40, h - 20))
            dx = random.choice([-0.45, -0.25, -0.12, 0.12, 0.25, 0.45])
            dy = random.choice([-0.4, -0.18, 0.18, 0.4])
            sym = random.choice(_SYMBOLS)
            color = random.choice([PRIMARY, PURPLE, MUTED, GLOW_BLUE, GLOW_PURPLE, GREEN])
            item = self.create_text(
                x,
                y,
                text=sym,
                fill=color,
                font=(FONT_MONO, random.choice([10, 12, 14, 16])),
                tags="particle",
            )
            self.particles.append([item, dx, dy])
        self._tick()

    def _tick(self):
        if not self._alive:
            return
        try:
            if not self.winfo_exists():
                self._alive = False
                return
            w = max(self.winfo_width(), 2)
            h = max(self.winfo_height(), 2)
            for particle in self.particles:
                item, dx, dy = particle
                self.move(item, dx, dy)
                x, y = self.coords(item)
                if x < 10 or x > w - 10:
                    particle[1] *= -1
                if y < 10 or y > h - 10:
                    particle[2] *= -1
            if self._alive:
                job = self.after(40, self._tick)
                self.jobs.append(job)
        except tk.TclError:
            self._alive = False


def pulse_label(label, colors, jobs, delay=420):
    state = {"i": 0}

    def tick():
        try:
            if not label.winfo_exists():
                return
            label.configure(fg=colors[state["i"] % len(colors)])
            state["i"] += 1
            jobs.append(label.after(delay, tick))
        except tk.TclError:
            return

    tick()


def _center_dialog(root, win):
    win.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - win.winfo_reqwidth()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - win.winfo_reqheight()) // 2
    win.geometry(f"+{max(x, 40)}+{max(y, 40)}")


def themed_confirm(root, title, message, yes_text="Confirm", no_text="Cancel"):
    result = {"ok": False}
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()

    wrap, card = glass_card(win, padx=28, pady=22)
    wrap.pack(padx=18, pady=18)

    section_title(card, title, WHITE, 18, CARD).pack(anchor="w")
    muted_label(card, message, 12, CARD).pack(anchor="w", pady=(8, 18))

    actions = tk.Frame(card, bg=CARD)
    actions.pack(anchor="e")

    def yes():
        result["ok"] = True
        win.destroy()

    def no():
        win.destroy()

    styled_button(actions, no_text, no, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=12, height=1).pack(
        side="left", padx=6
    )
    styled_button(actions, yes_text, yes, bg=RED, hover="#F87171", width=12, height=1).pack(side="left", padx=6)

    _center_dialog(root, win)
    win.bind("<Escape>", lambda e: no())
    win.wait_window()
    return result["ok"]


def themed_alert(root, title, message, ok_text="OK"):
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()

    wrap, card = glass_card(win, padx=28, pady=22)
    wrap.pack(padx=18, pady=18)
    section_title(card, title, WHITE, 18, CARD).pack(anchor="w")
    muted_label(card, message, 12, CARD).pack(anchor="w", pady=(8, 18))

    def close():
        win.destroy()

    styled_button(card, ok_text, close, bg=PRIMARY, hover=GLOW_BLUE, width=14, height=1).pack(anchor="e")
    _center_dialog(root, win)
    win.bind("<Escape>", lambda e: close())
    win.bind("<Return>", lambda e: close())
    win.wait_window()

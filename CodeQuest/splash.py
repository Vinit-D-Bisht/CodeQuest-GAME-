import tkinter as tk
from constants import *
import theme

def show(root, callback):
    splash = tk.Frame(root, bg=BG)
    splash.place(relwidth=1, relheight=1)

    jobs = []
    canvas = theme.ParticleCanvas(splash, jobs)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

    card_wrap, card = theme.glass_card(splash, padx=40, pady=32)
    card_wrap.place(relx=0.5, rely=0.5, anchor="center")

    logo = tk.Label(
        card,
        text="</>",
        font=(FONT_MONO, 42, "bold"),
        fg=PRIMARY,
        bg=CARD,
    )
    logo.pack(pady=(4, 2))
    theme.pulse_label(logo, [PRIMARY, PURPLE, GLOW_BLUE], jobs, 360)

    tk.Label(
        card,
        text="CODEQUEST",
        font=(FONT, 34, "bold"),
        fg=WHITE,
        bg=CARD,
    ).pack()

    tk.Label(
        card,
        text="Master the Code  •  Conquer the Quest",
        font=(FONT, 13),
        fg=MUTED,
        bg=CARD,
    ).pack(pady=(4, 18))

    loading = tk.Label(
        card,
        text="Initializing systems",
        font=(FONT_MONO, 12),
        fg=GOLD,
        bg=CARD,
    )
    loading.pack()

    bar_host = tk.Frame(card, bg=CARD2, height=10, width=280, highlightthickness=0, bd=0)
    bar_host.pack(pady=16)
    bar_host.pack_propagate(False)
    fill = tk.Frame(bar_host, bg=PRIMARY, width=8, height=10)
    fill.place(x=0, y=0, height=10)

    def animate(count=0):
        if not splash.winfo_exists():
            return
        dots = "." * (count % 4)
        try:
            loading.config(text=f"Initializing systems{dots}")
            fill.place(width=min(280, 12 + count * 14))
        except tk.TclError:
            return
        if count < 20:
            jobs.append(root.after(140, animate, count + 1))

    animate()

    def finish():
        canvas.shutdown()
        for job in list(jobs):
            try:
                root.after_cancel(job)
            except Exception:
                pass
        jobs.clear()
        callback()

    root.after(2800, finish)

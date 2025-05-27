# run.py - Avvio semplice e pulito dell'app GUI

from app.gui import App
import tkinter as tk
from tkinter import ttk
import os

if __name__ == "__main__":
    root = tk.Tk()
    root.title("DCST Tool")

    # Imposta icona se disponibile
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(default=icon_path)
        except:
            pass  # Evita crash se l'icona non è compatibile

    # Crea barra di progresso e avvia l'app
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    app = App(root, progress_bar)

    root.mainloop()

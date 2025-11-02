#!/usr/bin/env python3
"""
DCST Tool - Minimal startup
Opens the minimal GUI directly without splash screens, themes, or extra effects.
"""

import tkinter as tk


def main():
    try:
        from app.gui import App  # Minimal GUI
    except Exception as e:
        import traceback
        print(f"Failed to load GUI: {e}")
        traceback.print_exc()
        raise

    root = tk.Tk()
    root.title("DCST Tool")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

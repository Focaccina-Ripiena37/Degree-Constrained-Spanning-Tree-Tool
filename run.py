# run.py - Esegue l'applicazione

# Importazioni della libreria standard
import os
import sys
import logging
from tkinter import Tk
from tkinter import ttk
from functools import partial

def configure_environment():
    """Configura l'ambiente per l'applicazione"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    # Crea la cartella per i plot
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    plot_dir = os.path.join(desktop_path, "Plot")
    os.makedirs(plot_dir, exist_ok=True)
    
    # Configura il logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(desktop_path, "dcst_app.log"))
        ]
    )
    logging.info("Ambiente configurato correttamente.")

# Esegui l'applicazione
if __name__ == "__main__":
    configure_environment()
    
    try:
        from app.gui import App
        
        logging.info("Algoritmi caricati correttamente.")
        
        # Inizializza la GUI dell'applicazione
        logging.info("Moduli dell'applicazione importati correttamente.")
        root = Tk()

        # Imposta l'icona personalizzata
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(default=icon_path)
        else:
            logging.warning(f"Icona non trovata: {icon_path}")

        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        app = App(root, progress_bar)
        
        # Definisci la funzione di chiusura dell'applicazione
        def on_closing():
            logging.info("Chiusura dell'applicazione...")
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Avvia il mainloop
        root.mainloop()
        logging.info("GUI avviata con successo.")
        
    # Gestione degli errori    
    except Exception as e:
        logging.error(f"Errore critico: {str(e)}")
        logging.exception("Traceback:")
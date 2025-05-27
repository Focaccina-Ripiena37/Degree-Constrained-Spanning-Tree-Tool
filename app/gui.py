# app/gui.py - Interfaccia grafica dell'applicazione

# Import delle librerie standard
import os
import time
import queue
import logging
import threading
import webbrowser
import tkinter as tk
from functools import partial
from tkinter import messagebox, scrolledtext, ttk

# Import delle librerie di terze parti
import pandas as pd
from PIL import Image, ImageTk

# Import degli algortimi locali
from .algorithms import test_instance
from .utils import generate_connected_random_graph, draw_and_save_graph, save_table_as_image
from .algorithms import (
    greedy_spanning_tree,
    calculate_cost_base,
    adaptive_neighborhood_local_search
)
from .utils import generate_connected_random_graph, draw_and_save_graph, save_table_as_image

# Classe per la gestione dei messaggi di log
class QueueHandler(logging.Handler):
    """Handler personalizzato che invia i messaggi di log alla coda dell'interfaccia."""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        level_name = record.levelname.lower()
        level = "info"
        if level_name == "error" or level_name == "critical":
            level = "error"
        elif level_name == "warning":
            level = "warning"
        elif level_name == "info":
            level = "info"
        self.queue.put(("log", (msg, level)))

# Classe per l'interfaccia grafica dell'applicazione
class App:
    def __init__(self, root, progress_bar):
        self.root = root
        self.progress_bar = progress_bar
        self.root.title("DCST Tool")
        self.root.geometry("400x780")
        self.root.configure(bg="#2b2b2b")  # Tema scuro

        # Variabili di controllo
        self.n_small = tk.IntVar(value=10)
        self.n_medium = tk.IntVar(value=50)
        self.n_large = tk.IntVar(value=200)
        self.p_val = tk.DoubleVar(value=0.3)
        self.max_children = tk.IntVar(value=3)
        self.penalty = tk.IntVar(value=1000)

        # Variabili per il tracciamento del progresso
        self.current_algorithm = ""
        self.current_instance = ""
        self.current_phase = ""

        # Variabile per il thread di calcolo
        self.computation_thread = None
        self.stop_event = threading.Event()
        self.queue_running = True  # Flag per controllare il thread della coda

        # Etichette e campi di input
        self.create_widgets()

        # Barra di avanzamento
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=5)

        # Etichetta per lo stato della progress bar
        self.progress_label = tk.Label(self.root, text="Pronto per avviare...", fg="white", bg="#2b2b2b")
        self.progress_label.pack(pady=2)

        # Area di testo con scrollbar per dettagli dell'esecuzione
        self.log_frame = tk.Frame(self.root, bg="#2b2b2b")
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Etichetta per il log
        self.log_header = tk.Label(self.log_frame, text="Performance Details", bg="#2b2b2b", fg="white", anchor="w", font=("Arial", 10, "bold"))
        self.log_header.pack(fill="x", padx=5, pady=2)

        self.log_text = tk.scrolledtext.ScrolledText(self.log_frame, height=10, bg="#1e1e1e", fg="#cccccc",
                                                wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state=tk.DISABLED)  # Read-only

        # Configure text tags for different log levels and performance metrics
        self.log_text.tag_config("timestamp", foreground="#999999")
        self.log_text.tag_config("info", foreground="#cccccc")
        self.log_text.tag_config("success", foreground="#00cc00")
        self.log_text.tag_config("warning", foreground="#ffcc00")
        self.log_text.tag_config("error", foreground="#ff3333")
        self.log_text.tag_config("highlight", foreground="#3399ff")
        self.log_text.tag_config("performance", foreground="#ff9900")  # Orange for performance metrics

        # Pannello per i parametri dinamici - Layout migliorato
        self.dynamic_params_frame = tk.LabelFrame(self.root, text="Parametri in tempo reale",
                                                bg="#2b2b2b", fg="white",
                                                font=("Arial", 9, "bold"),
                                                relief="groove", bd=2)
        self.dynamic_params_frame.pack(fill="x", padx=10, pady=(5, 10))

        # Configura le colonne per una distribuzione uniforme
        for i in range(3):
            self.dynamic_params_frame.columnconfigure(i, weight=1, uniform="equal")

        # Prima riga: Parametri principali dell'algoritmo
        self.iter_label = tk.Label(self.dynamic_params_frame, text="Iterazioni: -",
                                 bg="#2b2b2b", fg="#87CEEB", font=("Arial", 8, "bold"),
                                 anchor="w", width=15)
        self.iter_label.grid(row=0, column=0, padx=8, pady=4, sticky="ew")

        self.temp_label = tk.Label(self.dynamic_params_frame, text="Temperatura: -",
                                 bg="#2b2b2b", fg="#87CEEB", font=("Arial", 8, "bold"),
                                 anchor="w", width=15)
        self.temp_label.grid(row=0, column=1, padx=8, pady=4, sticky="ew")

        self.cost_label = tk.Label(self.dynamic_params_frame, text="Costo attuale: -",
                                 bg="#2b2b2b", fg="#90EE90", font=("Arial", 8, "bold"),
                                 anchor="w", width=15)
        self.cost_label.grid(row=0, column=2, padx=8, pady=4, sticky="ew")

        # Seconda riga: Metriche di performance
        self.accepted_label = tk.Label(self.dynamic_params_frame, text="Accettazioni: -",
                                     bg="#2b2b2b", fg="#90EE90", font=("Arial", 8, "bold"),
                                     anchor="w", width=15)
        self.accepted_label.grid(row=1, column=0, padx=8, pady=4, sticky="ew")

        self.plateau_label = tk.Label(self.dynamic_params_frame, text="Plateau: -",
                                    bg="#2b2b2b", fg="#FFA500", font=("Arial", 8, "bold"),
                                    anchor="w", width=15)
        self.plateau_label.grid(row=1, column=1, padx=8, pady=4, sticky="ew")

        self.reheat_label = tk.Label(self.dynamic_params_frame, text="Reheat: -",
                                   bg="#2b2b2b", fg="#FFA500", font=("Arial", 8, "bold"),
                                   anchor="w", width=15)
        self.reheat_label.grid(row=1, column=2, padx=8, pady=4, sticky="ew")

        # Terza riga: Spazio per metriche aggiuntive future (opzionale)
        # Questa riga può essere utilizzata per aggiungere nuove metriche senza modificare il layout
        self.extra_metric1_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg="#2b2b2b", fg="#DDA0DD", font=("Arial", 8),
                                          anchor="w", width=15)
        self.extra_metric1_label.grid(row=2, column=0, padx=8, pady=2, sticky="ew")

        self.extra_metric2_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg="#2b2b2b", fg="#DDA0DD", font=("Arial", 8),
                                          anchor="w", width=15)
        self.extra_metric2_label.grid(row=2, column=1, padx=8, pady=2, sticky="ew")

        self.extra_metric3_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg="#2b2b2b", fg="#DDA0DD", font=("Arial", 8),
                                          anchor="w", width=15)
        self.extra_metric3_label.grid(row=2, column=2, padx=8, pady=2, sticky="ew")

        # Coda per la comunicazione tra thread
        self.queue = queue.Queue()
        self.queue_handler = QueueHandler(self.queue)
        logging.getLogger().addHandler(self.queue_handler)

        # Avvia il thread per il processamento della coda
        self.queue_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.queue_thread.start()

        # Chiudere il terminale quando la finestra viene chiusa
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        frame = tk.Frame(self.root, bg="#2b2b2b")
        frame.pack(pady=10)  # Adjusted padding to move the title lower
        # Titolo (centrato sopra gli input)
        title_label = tk.Label(frame, text="DCST Tool", font=("Arial", 16, "bold"), fg="white", bg="#2b2b2b")
        title_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))  # Spanning due colonne

        # Titolo
        #self.center_title()

        # Aggiungere l'icona GitHub
        self.add_github_icon(frame)

        # Input per il numero di nodi
        tk.Label(frame, text="Istanza piccola:", fg="white", bg="#2b2b2b").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.n_small, width=10).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(frame, text="Istanza media:", fg="white", bg="#2b2b2b").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.n_medium, width=10).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(frame, text="Istanza grande:", fg="white", bg="#2b2b2b").grid(row=3, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.n_large, width=10).grid(row=3, column=1, padx=5, pady=5)

        # Input per max_children (k)
        tk.Label(frame, text="Numero massimo di figli:", fg="white", bg="#2b2b2b").grid(row=4, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.max_children, width=10).grid(row=4, column=1, padx=5, pady=5)

        tk.Label(frame, text="Penalità:", fg="white", bg="#2b2b2b").grid(row=5, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.penalty, width=10).grid(row=5, column=1, padx=5, pady=5)

        # Slider per il parametro p (connettività)
        tk.Label(frame, text="Grado di connessione:", fg="white", bg="#2b2b2b").grid(row=6, column=0, padx=5, pady=5)
        tk.Scale(frame, variable=self.p_val, from_=0, to=1, resolution=0.01, orient="horizontal", bg="#2b2b2b", fg="white").grid(row=6, column=1, padx=5, pady=5)

        # Bottone per avviare i calcoli
        start_button = tk.Button(frame, text="Avvia", command=self.start_computation, bg="#3399ff", fg="white")
        start_button.grid(row=7, column=0, pady=20)

        # Bottone per fermare i calcoli
        stop_button = tk.Button(frame, text="Stop", command=self.stop_computation, bg="#ff3333", fg="white")
        stop_button.grid(row=7, column=1, pady=20)

        # Etichetta per i dettagli di stato
        self.status_details = tk.Label(self.root, text="", fg="lightblue", bg="#2b2b2b", wraplength=300)
        self.status_details.pack(pady=5)

    #def center_title(self):
        #title_label = tk.Label(self.root, text="DCST Tool", font=("Arial", 16), fg="white", bg="#2b2b2b")
        #title_label.pack(pady=10)
        #title_label.place(relx=0.5, rely=0.05, anchor='center')

    def add_github_icon(self, frame):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "github.png")
            if os.path.exists(icon_path):
                pil_image = Image.open(icon_path)
                github_icon = ImageTk.PhotoImage(pil_image)
                github_button = tk.Button(
                    frame,
                    image=github_icon,
                    command=self.open_github,
                    bg="#2b2b2b",
                    borderwidth=0
                )
                github_button.image = github_icon
                github_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")  # Positioned to the right of the title
            else:
                print(f"File non trovato: {icon_path}")
        except Exception as e:
            print(f"Errore nel caricamento dell'icona: {str(e)}")

    def open_github(self):
        webbrowser.open("https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git")

    def validate_inputs(self):
        """Verifica che i valori inseriti siano coerenti e visualizza un messaggio di errore se non lo sono."""
        try:
            n_small = int(self.n_small.get())
            n_medium = int(self.n_medium.get())
            n_large = int(self.n_large.get())
        except ValueError:
            messagebox.showerror("Errore di input", "I valori devono essere numeri interi.")
            return False

        if n_small <= 0 or n_medium <= 0 or n_large <= 0:
            messagebox.showerror("Errore di input", "I valori devono essere numeri positivi e maggiori di zero.")
            return False

        if not (n_small < n_medium < n_large):
            messagebox.showerror("Errore di input", "I valori devono rispettare la gerarchia:\n"
                                                    "Istanza Piccola < Istanza Media < Istanza Grande")
            return False

        return True

    def start_computation(self):
        """Avvia i calcoli per tutte le istanze."""
        self.reset_progress_bar()
        self.progress_label.config(text="Pronto per avviare...")

        if not self.validate_inputs():
            return

        self.stop_event.clear()

        # Avvia un thread separato per eseguire i calcoli
        self.computation_thread = threading.Thread(target=self.run_optimization, daemon=True)
        self.computation_thread.start()

    def stop_computation(self):
        """Interrompe i calcoli in corso."""
        if self.computation_thread and self.computation_thread.is_alive():
            # Imposta l'evento di stop
            self.stop_event.set()
            self.queue.put(("status", "Interruzione in corso..."))
            self.queue.put(("progress", 0))  # Resetta la progress bar

            # Attendi che il thread di calcolo termini (con timeout)
            self.computation_thread.join(timeout=5)  # Aspetta al massimo 5 secondi
            if self.computation_thread.is_alive():
                logging.warning("Thread di calcolo non è terminato entro il timeout.")

            # Salva i risultati parziali
            self.save_partial_results()

            # Notifica l'utente
            self.queue.put(("status", "Calcolo interrotto dall'utente. Salvataggio dei risultati parziali..."))
            messagebox.showinfo("Interrotto", "L'esecuzione è stata interrotta. I risultati parziali sono stati salvati.")

    def save_partial_results(self):
        """Salva i risultati parziali generati fino a quel momento."""
        try:
            results = getattr(self, "results", {})  # Recupera i risultati parziali
            if not results:
                logging.info("Nessun risultato parziale da salvare.")
                return

            plot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Plot")
            os.makedirs(plot_dir, exist_ok=True)

            for size_name, instance_results in results.items():
                if "graph" in instance_results:
                    graph_filename = os.path.join(plot_dir, f"partial_graph_{size_name}.png")
                    draw_and_save_graph(instance_results["graph"], graph_filename, max_children=self.max_children.get(), is_spanning_tree=False)

                for algo in ["greedy", "local", "sa"]:
                    tree_key = f"{algo}_tree"
                    if tree_key in instance_results:
                        tree_filename = os.path.join(plot_dir, f"partial_{algo}_tree_{size_name}.png")
                        draw_and_save_graph(instance_results[tree_key], tree_filename, max_children=self.max_children.get(), is_spanning_tree=True)

            # Salva anche le tabelle parziali
            table_data = []
            for size_name, metrics in results.items():
                for algo in ["greedy", "local", "sa"]:
                    algo_key = f"{algo}_cost"
                    if algo_key in metrics:
                        row = {
                            "Istanza": size_name,
                            "Algoritmo": algo.capitalize(),
                            "Costo": metrics[algo_key],
                            "Tempo (s)": round(metrics[f"{algo}_time"], 4),
                            "Chiamate": metrics[f"{algo}_calls"],
                            "Memoria (KB)": round(metrics[f"{algo}_memory"], 2),
                            "Violazioni": metrics.get(f"{algo}_violations", 0)
                        }
                        table_data.append(row)

            if table_data:
                # Calcola i punteggi per i risultati parziali
                from .algorithms import evaluate_solution

                # Calcola i valori massimi per la normalizzazione
                max_cost = max(row["Costo"] for row in table_data)
                max_time = max(row["Tempo (s)"] for row in table_data)
                max_memory = max(row["Memoria (KB)"] for row in table_data)
                max_violations = max(row["Violazioni"] for row in table_data)

                reference_values = {
                    "max_cost": max_cost,
                    "max_time": max_time,
                    "max_memory": max_memory,
                    "max_violations": max_violations
                }

                # Calcola il punteggio per ogni riga
                for row in table_data:
                    solution_data = {
                        "cost": row["Costo"],
                        "execution_time": row["Tempo (s)"],
                        "memory": row["Memoria (KB)"],
                        "violations": row["Violazioni"]
                    }

                    score = evaluate_solution(solution_data, reference_values)
                    row["Punteggio"] = score

                df = pd.DataFrame(table_data)
                table_filename = os.path.join(plot_dir, "partial_results_table.png")
                save_table_as_image(df, table_filename)
                logging.info(f"Tabella parziale salvata: {table_filename}")

            # Genera anche i grafici temporali parziali se disponibili
            from .utils import plot_score_evolution

            for size_name, instance_results in results.items():
                score_histories = {}

                if "local_score_history" in instance_results and instance_results["local_score_history"]:
                    score_histories["Local Search"] = instance_results["local_score_history"]

                if "sa_score_history" in instance_results and instance_results["sa_score_history"]:
                    score_histories["Simulated Annealing"] = instance_results["sa_score_history"]

                if score_histories:
                    # Calcola valori di riferimento parziali
                    all_costs = []
                    all_times = []
                    all_memories = []
                    all_violations = []

                    for algo in ["greedy", "local", "sa"]:
                        if f"{algo}_cost" in instance_results:
                            all_costs.append(instance_results[f"{algo}_cost"])
                        if f"{algo}_time" in instance_results:
                            all_times.append(instance_results[f"{algo}_time"])
                        if f"{algo}_memory" in instance_results:
                            all_memories.append(instance_results[f"{algo}_memory"])
                        if f"{algo}_violations" in instance_results:
                            all_violations.append(instance_results[f"{algo}_violations"])

                    reference_final_values = {
                        "max_cost": max(all_costs) if all_costs else 1,
                        "max_time": max(all_times) if all_times else 1,
                        "max_memory": max(all_memories) if all_memories else 1,
                        "max_violations": max(all_violations) if all_violations else 1
                    }

                    evolution_filename = f"partial_evoluzione_punteggio_{size_name}.png"
                    success = plot_score_evolution(score_histories, reference_final_values, evolution_filename)
                    if success:
                        logging.info(f"Grafico evoluzione parziale salvato per {size_name}")

            logging.info("Risultati parziali salvati con successo.")

        except Exception as e:
            logging.error(f"Errore durante il salvataggio dei risultati parziali: {e}")

    def log_message(self, message, level="info"):
        """Aggiunge un messaggio al log con timestamp."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Map degli stili di colore basati sul livello
        color_map = {
            "info": "#cccccc",      # grigio chiaro
            "success": "#00cc00",   # verde
            "warning": "#ffcc00",   # giallo
            "error": "#ff3333",     # rosso
            "highlight": "#3399ff", # blu
            "performance": "#ff9900" # arancione per metriche di performance
        }
        color = color_map.get(level, "#cccccc")

        # Evidenzia le metriche di performance nei messaggi normali
        if level in ["info", "success"] and any(x in message.lower() for x in ["costo=", "tempo=", "chiamate=", "memoria=", "iterazioni="]):
            # Messaggio con metriche di performance
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")

            # Separa e formatta parti del messaggio con metriche
            parts = []
            current_part = ""
            for segment in message.split(", "):
                if any(x in segment.lower() for x in ["costo=", "tempo=", "chiamate=", "memoria=", "iterazioni=", "accettazioni="]):
                    if current_part:
                        parts.append((current_part, level))
                        current_part = ""
                    parts.append((segment, "performance"))
                else:
                    current_part += (", " if current_part else "") + segment

            if current_part:
                parts.append((current_part, level))

            for part, tag in parts:
                self.log_text.insert(tk.END, part + (", " if tag == "performance" and part != parts[-1][0] else ""), tag)

            self.log_text.insert(tk.END, "\n")
        else:
            # Messaggio normale
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.log_text.insert(tk.END, f"{message}\n", level)

        self.log_text.see(tk.END)  # Scorre automaticamente alla fine
        self.log_text.config(state=tk.DISABLED)  # Torna in modalità di sola lettura

    def reset_progress_bar(self):
        """Resetta la progress bar e le etichette di stato con layout migliorato."""
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Pronto per avviare...")

        # Reset delle etichette dei parametri dinamici con ordine logico
        self.iter_label.config(text="Iterazioni: -")
        self.temp_label.config(text="Temperatura: -")
        self.cost_label.config(text="Costo attuale: -")
        self.accepted_label.config(text="Accettazioni: -")
        self.plateau_label.config(text="Plateau: -")
        self.reheat_label.config(text="Reheat: -")
        # Reset delle etichette extra
        self.extra_metric1_label.config(text="")
        self.extra_metric2_label.config(text="")
        self.extra_metric3_label.config(text="")

    def on_closing(self):
        """Gestisce la chiusura della finestra principale."""
        if messagebox.askokcancel("Esci", "Vuoi davvero uscire?"):
            self.queue_running = False  # Ferma il thread della coda
            self.stop_event.set()  # Ferma eventuali calcoli in corso
            self.root.destroy()

    def process_queue(self):
        """Processa i messaggi nella coda per aggiornamenti della GUI."""
        while self.queue_running:
            try:
                msg_type, msg_value = self.queue.get(block=True, timeout=0.1)

                self.root.after(0, self._process_message, msg_type, msg_value)

            except queue.Empty:
                time.sleep(0.01)  # Breve pausa per non saturare la CPU
            except Exception as e:
                print(f"Errore durante il processamento della coda: {e}")

    def _process_message(self, msg_type, msg_value):
        """Processa un singolo messaggio dalla coda (chiamato dal thread principale)."""
        try:
            if msg_type == "temperature":
                self.temp_label.config(text=f"Temperatura: {msg_value}")
            elif msg_type == "iteration":
                self.iter_label.config(text=f"Iterazioni: {msg_value}")
            elif msg_type == "cost":
                self.cost_label.config(text=f"Costo attuale: {msg_value}")
            elif msg_type == "plateau":
                self.plateau_label.config(text=f"Plateau: {msg_value}")
            elif msg_type == "reheats":
                self.reheat_label.config(text=f"Reheat: {msg_value}")
            elif msg_type == "accepted":
                self.accepted_label.config(text=f"Accettazioni: {msg_value}")
            elif msg_type == "log":
                msg, level = msg_value
                self.log_message(msg, level)
            elif msg_type == "progress":
                self.progress_bar['value'] = msg_value
                self.progress_label.config(text=f"Progresso: {msg_value}%")
            elif msg_type == "status":
                self.progress_label.config(text=msg_value)
            elif msg_type == "phase":
                self.status_details.config(text=msg_value)
            elif msg_type == "instance":
                self.current_instance = msg_value
            elif msg_type == "algorithm":
                self.current_algorithm = msg_value
            elif msg_type == "error":
                messagebox.showerror("Errore", msg_value)
                self.reset_progress_bar()
        except Exception as e:
            print(f"Errore durante l'elaborazione del messaggio {msg_type}: {e}")

    def run_optimization(self):
        """
        Esegue il calcolo per tutte le istanze (piccola, media, grande)
        con aggiornamenti dettagliati dello stato.
        """
        # Store results for later saving
        self.results = {}
        instances = {
            "piccola": self.n_small.get(),
            "media": self.n_medium.get(),
            "grande": self.n_large.get()
        }

        # Resetta le etichette dei parametri dinamici con layout migliorato
        self.iter_label.config(text="Iterazioni: -")
        self.temp_label.config(text="Temperatura: -")
        self.cost_label.config(text="Costo attuale: -")
        self.accepted_label.config(text="Accettazioni: -")
        self.plateau_label.config(text="Plateau: -")
        self.reheat_label.config(text="Reheat: -")
        # Reset delle etichette extra (se utilizzate)
        self.extra_metric1_label.config(text="")
        self.extra_metric2_label.config(text="")
        self.extra_metric3_label.config(text="")

        try:
            # Total progress = 100 units per instance
            # Calculate weighted steps based on instance size
            total_nodes = sum(instances.values())
            weighted_instances = {name: (size/total_nodes) * 100 for name, size in instances.items()}

            self.queue.put(("log", ("Inizializzazione dell'ottimizzazione...", "info")))
            self.queue.put(("log", (f"Parametri: max_children={self.max_children.get()}, penalty={self.penalty.get()}, p={self.p_val.get()}", "info")))

            # Reset overall progress
            overall_progress = 0
            self.queue.put(("progress", overall_progress))

            for idx, (instance_name, n_nodes) in enumerate(instances.items()):
                if self.stop_event.is_set():
                    self.queue.put(("log", ("Calcolo interrotto dall'utente.", "warning")))
                    break

                # Calculate instance weight for progress bar
                instance_weight = weighted_instances[instance_name]
                instance_progress_start = overall_progress

                # Aggiornamento per la nuova istanza
                self.queue.put(("instance", instance_name))
                self.queue.put(("log", (f"Generazione grafo casuale connesso con {n_nodes} nodi e p={self.p_val.get()}...", "info")))

                # Aggiorna la progress bar per la fase di generazione del grafo (10% dell'istanza)
                graph_gen_progress = instance_progress_start + (instance_weight * 0.1)
                self.queue.put(("progress", int(graph_gen_progress)))
                self.queue.put(("phase", f"Generazione grafo per istanza {instance_name}"))

                # Genera il grafo
                G = generate_connected_random_graph(n_nodes, float(self.p_val.get()))
                self.queue.put(("log", (f"Grafo generato: {n_nodes} nodi, {len(G.edges())} archi", "success")))

                # Update progress after graph generation (15% of instance progress)
                graph_complete_progress = instance_progress_start + (instance_weight * 0.15)
                self.queue.put(("progress", int(graph_complete_progress)))

                if self.stop_event.is_set():
                    self.queue.put(("log", ("Calcolo interrotto dall'utente.", "warning")))
                    break

                # Avvia il test dell'istanza
                self.queue.put(("phase", f"Ottimizzazione istanza {instance_name} ({n_nodes} nodi)"))
                self.queue.put(("log", (f"Avvio ottimizzazione per istanza {instance_name}...", "info")))

                # Informazioni di progresso per l'istanza
                progress_info = {
                    "start_progress": graph_complete_progress,
                    "total_progress": instance_weight * 0.85,
                    "queue": self.queue
                }

                # Esegui la simulazione per l'istanza corrente
                self.results[instance_name] = test_instance(
                    G, self.max_children.get(), self.penalty.get(),
                    instance_name=instance_name,
                    stop_event=self.stop_event,
                    queue=self.queue,
                    progress_info=progress_info
                )

                # Aggiorna il progresso complessivo dopo il completamento dell'istanza
                overall_progress = instance_progress_start + instance_weight
                self.queue.put(("progress", int(overall_progress)))
                self.queue.put(("log", (f"Ottimizzazione istanza {instance_name} completata", "success")))

                if self.stop_event.is_set():
                    self.queue.put(("log", ("Calcolo interrotto dall'utente.", "warning")))
                    break

            # Salva i risultati finali
            self.save_results(instances, self.max_children.get(), self.penalty.get(), self.results, os.path.join(os.path.expanduser("~"), "Desktop", "Plot"))
            self.queue.put(("log", ("Ottimizzazione completata.", "success")))
            self.queue.put(("progress", 100))

            # Mantieni la progress bar al 100% per 3 secondi poi resetta
            self.root.after(3000, self.reset_progress_bar)

        except Exception as e:
            self.queue.put(("error", f"Errore durante l'ottimizzazione: {str(e)}"))
            logging.error(f"Errore nell'ottimizzazione: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def save_results(self, instances, max_children, penalty, results, plot_dir):
        """
        Salva immagini dei grafi e tabelle di confronto per tutte le istanze.

        Args:
            instances (dict): Dizionario con i nomi delle istanze e il numero di nodi.
            max_children (int): Numero massimo di figli consentiti.
            penalty (int): Penalità applicata per violazioni del vincolo di grado.
            results (dict): Risultati delle ottimizzazioni per ogni istanza.
            plot_dir (str): Directory dove salvare le immagini e le tabelle.
        """
        try:
            os.makedirs(plot_dir, exist_ok=True)

            # Calcola il numero totale di immagini da creare per aggiornre la progress bar
            total_images = 0
            for size_name, instance_results in results.items():
                # Grafo iniziale
                if "graph" in instance_results:
                    total_images += 1

                # Alberi degli algoritmi
                for algo in ["greedy", "local", "sa"]:
                    tree_key = f"{algo}_tree"
                    if tree_key in instance_results:
                        total_images += 1

            # Aggiungine 1 per ogni tabella di confronto
            total_images += 1

            # Imposta il progresso iniziale per la creazione delle immagini
            # Utilizza l'ultimo 10% della barra di progresso per la creazione delle immagini
            start_progress = 90
            current_progress = start_progress
            progress_increment = 10 / total_images if total_images > 0 else 0

            self.queue.put(("phase", "Creazione e salvataggio immagini"))
            self.queue.put(("progress", int(current_progress)))

            # Parametri da includere nei nomi dei file
            # Rendere esplicito il valore di k (max_children) nel nome del file
            params_suffix = f"_k{max_children}_p{self.p_val.get():.2f}_pen{penalty}"

            # Mapping per i nomi estesi delle dimensioni
            dim_labels = {
                "piccola": "Piccola",
                "media": "Media",
                "grande": "Grande"
            }

            # Salvataggio delle immagini
            image_count = 0
            for size_name, instance_results in results.items():
                if "graph" in instance_results:
                    # Nuovo formato del nome del file includendo i parametri e la dimensione esplicita
                    dim_label = dim_labels.get(size_name, size_name)
                    graph_filename = os.path.join(plot_dir, f"grafo_iniziale_istanza{dim_label}_{size_name}_n{instances[size_name]}{params_suffix}.png")
                    self.queue.put(("log", (f"Creazione immagine grafo per istanza {dim_label} ({size_name})...", "info")))
                    self.queue.put(("status", f"Salvando grafo {dim_label} ({size_name})..."))
                    draw_and_save_graph(instance_results["graph"], graph_filename, max_children=max_children, is_spanning_tree=False)

                    # Aggiorna i progressi
                    image_count += 1
                    current_progress = start_progress + (image_count * progress_increment)
                    self.queue.put(("progress", int(current_progress)))
                    self.queue.put(("log", (f"Immagine grafo {dim_label} ({size_name}) salvata: {graph_filename}", "success")))

                # Salvataggio degli alberi
                for algo in ["greedy", "local", "sa"]:
                    tree_key = f"{algo}_tree"
                    if tree_key in instance_results:
                        # Nuovo formato dei nomi dei file per gli alberi
                        algo_labels = {"greedy": "Greedy", "local": "LocalSearch", "sa": "SimulatedAnnealing"}
                        dim_label = dim_labels.get(size_name, size_name)
                        tree_filename = os.path.join(plot_dir, f"albero_{algo_labels[algo]}_istanza{dim_label}_{size_name}_n{instances[size_name]}{params_suffix}.png")

                        algo_name = {"greedy": "Greedy", "local": "Local Search", "sa": "Simulated Annealing"}
                        self.queue.put(("log", (f"Creazione immagine albero {algo_name.get(algo, algo)} per istanza {dim_label} ({size_name})...", "info")))
                        self.queue.put(("status", f"Salvando albero {algo_name.get(algo, algo)} {dim_label} ({size_name})..."))
                        draw_and_save_graph(instance_results[tree_key], tree_filename, max_children=max_children, is_spanning_tree=True)

                        # Aggiorna i progressi
                        image_count += 1
                        current_progress = start_progress + (image_count * progress_increment)
                        self.queue.put(("progress", int(current_progress)))
                        self.queue.put(("log", (f"Immagine albero {algo_name.get(algo, algo)} per istanza {dim_label} ({size_name}) salvata: {tree_filename}", "success")))

            # Salva anche le tabelle di confronto
            self.queue.put(("status", "Creazione tabella comparativa..."))
            self.queue.put(("log", ("Preparazione tabella di confronto...", "info")))
            table_data = []
            for size_name, metrics in results.items():
                dim_label = dim_labels.get(size_name, size_name)
                for algo in ["greedy", "local", "sa"]:
                    algo_key = f"{algo}_cost"
                    if algo_key in metrics:

                        calls = metrics.get(f"{algo}_calls", 0)
                        iterations = metrics.get(f"{algo}_iterations", calls)

                        # Per tutti gli algoritmi mostra il numero di chiamate
                        calls_display = calls
                        if (algo == "sa" and "sa_iterations" in metrics) or (algo == "local" and "local_iterations" in metrics) or (algo == "greedy" and "greedy_iterations" in metrics):
                            # Se disponibili mostra la metrica iter.
                            calls_display = f"{calls} ({iterations} iter.)"

                        # Aggiungi le righe alla tabella
                        row = {
                            "Istanza": f"{dim_label} ({size_name})",
                            "Algoritmo": algo.capitalize(),
                            "Costo": metrics[algo_key],
                            "Tempo (s)": self.format_time(metrics[f"{algo}_time"]),
                            "Chiamate": calls_display,
                            "Memoria (KB)": round(metrics[f"{algo}_memory"], 2),
                            "Violazioni": metrics.get(f"{algo}_violations", 0)
                        }

                        table_data.append(row)

            # Calcola i punteggi dopo aver raccolto tutti i dati
            if table_data:
                # Importa la funzione di valutazione
                from .algorithms import evaluate_solution

                # Calcola i valori massimi per la normalizzazione
                max_cost = max(row["Costo"] for row in table_data)
                max_time = max(float(str(row["Tempo (s)"]).replace("e", "E")) if "e" in str(row["Tempo (s)"]) else float(row["Tempo (s)"]) for row in table_data)
                max_memory = max(row["Memoria (KB)"] for row in table_data)
                max_violations = max(row["Violazioni"] for row in table_data)

                reference_values = {
                    "max_cost": max_cost,
                    "max_time": max_time,
                    "max_memory": max_memory,
                    "max_violations": max_violations
                }

                # Calcola il punteggio per ogni riga
                for row in table_data:
                    time_value = float(str(row["Tempo (s)"]).replace("e", "E")) if "e" in str(row["Tempo (s)"]) else float(row["Tempo (s)"])
                    solution_data = {
                        "cost": row["Costo"],
                        "execution_time": time_value,
                        "memory": row["Memoria (KB)"],
                        "violations": row["Violazioni"]
                    }

                    score = evaluate_solution(solution_data, reference_values)
                    row["Punteggio"] = score

            if table_data:
                df = pd.DataFrame(table_data)

                # Trova e evidenzia la soluzione migliore
                best_solution = df.loc[df["Punteggio"].idxmax()]
                self.queue.put(("log", ("🏆 MIGLIORE SOLUZIONE TROVATA:", "highlight")))
                self.queue.put(("log", (f"{best_solution['Istanza']} - {best_solution['Algoritmo']}: "
                                      f"Punteggio={best_solution['Punteggio']}, Costo={best_solution['Costo']}, "
                                      f"Violazioni={best_solution['Violazioni']}, Tempo={best_solution['Tempo (s)']}", "success")))

                # Carica l'intera tabella di confronto nei log
                self.queue.put(("log", ("Tabella completa dei risultati:", "highlight")))
                for index, row in df.iterrows():
                    self.queue.put(("log", (f"{row['Istanza']} - {row['Algoritmo']}: Punteggio={row['Punteggio']}, "
                                          f"Costo={row['Costo']}, Violazioni={row['Violazioni']}, "
                                          f"Tempo={row['Tempo (s)']}, Chiamate={row['Chiamate']}, "
                                          f"Memoria={row['Memoria (KB)']} KB", "performance")))

                # Nuovo formato del nome file per la tabella
                table_filename = os.path.join(plot_dir, f"tabella_confronto{params_suffix}.png")
                save_table_as_image(df, table_filename)

                # Aggiorna i progressi per l'ultima immagine
                image_count += 1
                current_progress = start_progress + (image_count * progress_increment)
                self.queue.put(("progress", int(current_progress)))
                self.queue.put(("log", (f"Tabella di confronto salvata: {table_filename}", "success")))

            # Genera i grafici temporali dell'evoluzione del punteggio per ogni istanza
            self.queue.put(("status", "Generazione grafici evoluzione punteggio..."))
            self.queue.put(("log", ("Creazione grafici temporali evoluzione punteggio...", "info")))

            from .utils import plot_score_evolution

            for size_name, instance_results in results.items():
                # Raccoglie gli storici dei punteggi per questa istanza
                score_histories = {}

                if "local_score_history" in instance_results and instance_results["local_score_history"]:
                    score_histories["Local Search"] = instance_results["local_score_history"]

                if "sa_score_history" in instance_results and instance_results["sa_score_history"]:
                    score_histories["Simulated Annealing"] = instance_results["sa_score_history"]

                # Genera il grafico solo se ci sono dati
                if score_histories:
                    # Calcola i valori di riferimento finali per normalizzazione
                    all_costs = []
                    all_times = []
                    all_memories = []
                    all_violations = []

                    # Raccoglie tutti i valori finali dagli algoritmi
                    for algo in ["greedy", "local", "sa"]:
                        if f"{algo}_cost" in instance_results:
                            all_costs.append(instance_results[f"{algo}_cost"])
                        if f"{algo}_time" in instance_results:
                            all_times.append(instance_results[f"{algo}_time"])
                        if f"{algo}_memory" in instance_results:
                            all_memories.append(instance_results[f"{algo}_memory"])
                        if f"{algo}_violations" in instance_results:
                            all_violations.append(instance_results[f"{algo}_violations"])

                    # Calcola i valori di riferimento finali
                    reference_final_values = {
                        "max_cost": max(all_costs) if all_costs else 1,
                        "max_time": max(all_times) if all_times else 1,
                        "max_memory": max(all_memories) if all_memories else 1,
                        "max_violations": max(all_violations) if all_violations else 1
                    }

                    dim_label = dim_labels.get(size_name, size_name)
                    evolution_filename = f"evoluzione_punteggio_istanza{dim_label}_{size_name}_n{instances[size_name]}{params_suffix}.png"

                    self.queue.put(("log", (f"Creazione grafico evoluzione per istanza {dim_label} ({size_name})...", "info")))
                    success = plot_score_evolution(score_histories, reference_final_values, evolution_filename)

                    if success:
                        self.queue.put(("log", (f"Grafico evoluzione per istanza {dim_label} ({size_name}) salvato", "success")))
                    else:
                        self.queue.put(("log", (f"Errore nella creazione del grafico evoluzione per istanza {dim_label} ({size_name})", "error")))

            self.queue.put(("status", "Tutte le immagini create con successo"))
            self.queue.put(("progress", 100))  # Assicura che la progress bar arrivi al 100%
            self.queue.put(("log", ("Risultati salvati con successo.", "success")))

        except Exception as e:
            logging.error(f"Errore durante il salvataggio dei risultati: {e}")
            self.queue.put(("log", (f"Errore durante il salvataggio dei risultati: {e}", "error")))

    def format_time(self, time_value):
        """
        Formattare un valore temporale in secondi in una stringa con la precisione adeguata.
        Per valori piccoli (< 0,1), utilizzare la notazione scientifica.
        Per valori medi (< 1), arrotondare alla 4a cifra decimale.
        Per valori maggiori, arrotondare a 2 cifre decimali.
        """
        if time_value < 0.1:
            return f"{time_value:.4e}"
        elif time_value < 1:
            return f"{time_value:.4f}"
        else:
            return f"{time_value:.2f}"

if __name__ == "__main__":
    root = tk.Tk()
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    app = App(root, progress_bar)
    root.mainloop()
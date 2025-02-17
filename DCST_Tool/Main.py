import networkx as nx
import matplotlib.pyplot as plt
import random
import math
import time
import os
import pandas as pd
from tabulate import tabulate
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tqdm import tqdm
import threading
import queue
import webbrowser
from PIL import Image, ImageTk  # Aggiungi con gli altri import


# Lista dei moduli richiesti
required_modules = [
    "networkx",
    "matplotlib",
    "pandas",
    "tabulate",
    "numpy", 
    "tkinter",  # Correzione del nome del modulo
    "tqdm"
]

# Funzione per verificare l'installazione dei moduli
def check_modules(modules):
    missing_modules = []
    for module in modules:
        try:
            __import__(module)
            print(f"Modulo {module} trovato.")
        except ImportError:
            missing_modules.append(module)
            print(f"Errore: Il modulo {module} non è installato.")
    
    if missing_modules:
        print("\nInstallare i moduli mancanti utilizzando pip:")
        for module in missing_modules:
            print(f"pip install {module}")
        input("Premi Enter per uscire...")  # Mantieni la finestra aperta
        exit()

# Verifica iniziale dei moduli
print("Verifica dei moduli necessari...")
check_modules(required_modules)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("DCST Tool")
        self.root.geometry("400x400")
        self.root.configure(bg="#2b2b2b")  # Tema scuro

        # Variabili di controllo
        self.n_small = tk.IntVar(value=10)  # Numero di nodi piccolo (default: 10)
        self.n_medium = tk.IntVar(value=50)  # Numero di nodi medio (default: 50)
        self.n_large = tk.IntVar(value=200)  # Numero di nodi grande (default: 200)

        # Variabile per il thread di calcolo
        self.computation_thread = None
        self.stop_event = threading.Event()

        # Etichette e campi di input
        self.create_widgets()

        # Barra di avanzamento
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Etichetta per lo stato della progress bar
        self.progress_label = tk.Label(self.root, text="", fg="white", bg="#2b2b2b")
        self.progress_label.pack()

        # Coda per la comunicazione tra thread
        self.queue = queue.Queue()

        # Controllo periodico della coda
        self.root.after(100, self.process_queue)

        # Aggiungere l'icona GitHub
        self.add_github_icon()

        # Chiudere il terminale quando la finestra viene chiusa
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        frame = tk.Frame(self.root, bg="#2b2b2b")
        frame.pack(pady=20)

        # Titolo
        title_label = tk.Label(frame, text="DCST Tool", font=("Arial", 16), fg="white", bg="#2b2b2b")
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Input per il numero di nodi
        tk.Label(frame, text="Istanza piccola:", fg="white", bg="#2b2b2b").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.n_small, width=10).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(frame, text="Istanza media:", fg="white", bg="#2b2b2b").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.n_medium, width=10).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(frame, text="Istanza grande:", fg="white", bg="#2b2b2b").grid(row=3, column=0, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.n_large, width=10).grid(row=3, column=1, padx=5, pady=5)

        # Bottone per avviare i calcoli
        start_button = tk.Button(frame, text="Avvia", command=self.start_computation, bg="#3399ff", fg="white")
        start_button.grid(row=4, column=0, pady=20)

        # Bottone per fermare i calcoli
        stop_button = tk.Button(frame, text="Stop", command=self.stop_computation, bg="#ff3333", fg="white")
        stop_button.grid(row=4, column=1, pady=20)

    def add_github_icon(self):
        try:
            from PIL import Image, ImageTk  # Aggiungi in cima al file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "github.png")
            
            if os.path.exists(icon_path):
                # Carica l'immagine con Pillow e convertila per Tkinter
                pil_image = Image.open(icon_path)
                github_icon = ImageTk.PhotoImage(pil_image)
                
                github_button = tk.Button(
                    self.root, 
                    image=github_icon, 
                    command=self.open_github, 
                    bg="#2b2b2b", 
                    borderwidth=0
                )
                github_button.image = github_icon
                github_button.place(relx=0.01, rely=0.99, anchor='sw')
            else:
                print(f"File non trovato: {icon_path}")
                
        except Exception as e:
            print(f"Errore nel caricamento dell'icona: {str(e)}")

    def open_github(self):
        webbrowser.open("https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git")

    def start_computation(self):
        try:
            # Leggere i valori dagli input
            n_small = self.n_small.get()
            n_medium = self.n_medium.get()
            n_large = self.n_large.get()

            if n_small <= 0 or n_medium <= 0 or n_large <= 0:
                raise ValueError("Il numero di nodi deve essere positivo.")

            # Resettare l'evento di stop
            self.stop_event.clear()

            # Avviare un thread separato per i calcoli
            self.computation_thread = threading.Thread(target=self.run_optimization, args=(n_small, n_medium, n_large))
            self.computation_thread.start()

        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def stop_computation(self):
        if self.computation_thread and self.computation_thread.is_alive():
            self.stop_event.set()
            self.computation_thread.join()
            self.progress_bar["value"] = 0
            self.progress_label.config(text="")
            messagebox.showinfo("Interrotto", "Calcolo interrotto dall'utente.")

    def run_optimization(self, n_small, n_medium, n_large):
        try:
            # Creazione della cartella "Plot" sulla Desktop dell'utente corrente
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            plot_dir = os.path.join(desktop_path, "Plot")

            try:
                # Crea la cartella Plot (se non esiste già)
                os.makedirs(plot_dir, exist_ok=True)
                
                # Verifica che la cartella sia stata creata correttamente
                if not os.path.isdir(plot_dir):
                    raise FileNotFoundError("La cartella Plot non è stata creata correttamente.")
                
                print(f"Cartella Plot creata in: {plot_dir}")
            except PermissionError:
                print("Errore: Non hai i permessi sufficienti per creare una cartella sul desktop.")
                self.queue.put(("error", "Non hai i permessi sufficienti per creare una cartella sul desktop."))
                return
            except Exception as e:
                print(f"Errore durante la creazione della cartella Plot: {e}")
                self.queue.put(("error", str(e)))
                return

            # Generare i grafici casuali pesati e connessi
            G_small = generate_connected_random_graph(n_small, p=0.5, seed=42)
            G_medium = generate_connected_random_graph(n_medium, p=0.1, seed=42)
            G_large = generate_connected_random_graph(n_large, p=0.05, seed=42)

            # Salvare il grafico dell'istanza piccola
            draw_and_save_graph(G_small, os.path.join(plot_dir, f"graph_small_{n_small}.png"))

            # Avviare i calcoli con barra di avanzamento
            steps = 3  # Uno step per ciascun tipo di istanza
            self.queue.put(("progress", 0, steps, "Inizio calcoli..."))

            for i, (G, size) in enumerate([(G_small, n_small), (G_medium, n_medium), (G_large, n_large)]):
                if self.stop_event.is_set():
                    self.queue.put(("info", "Calcolo interrotto dall'utente."))
                    return

                self.queue.put(("progress", i, steps, f"Calcolo per istanza con {size} nodi..."))
                metrics = test_instance(G, root=0, k=3)
                if metrics:
                    print(f"Risultati per istanza {size}:")
                    table_data = [
                        ["Strategia", "Costo", "Tempo (s)"],
                        ["Greedy", metrics['greedy_cost'], f"{metrics['greedy_time']:.4f}"],
                        ["Ricerca Locale", metrics['local_cost'], f"{metrics['local_time']:.4f}"],
                        ["Simulated Annealing", metrics['sa_cost'], f"{metrics['sa_time']:.4f}"]
                    ]
                    print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
                    # Salvare la tabella come immagine
                    save_table_as_image(table_data, os.path.join(plot_dir, f"results_{size}.png"))

                    # Salvare i grafici degli alberi di copertura per l'istanza piccola
                    if size == n_small:
                        draw_and_save_graph(metrics['greedy_tree'], os.path.join(plot_dir, f"greedy_tree_small_{n_small}.png"))
                        draw_and_save_graph(metrics['local_tree'], os.path.join(plot_dir, f"local_tree_small_{n_small}.png"))
                        draw_and_save_graph(metrics['sa_tree'], os.path.join(plot_dir, f"sa_tree_small_{n_small}.png"))
                else:
                    self.queue.put(("error", f"Impossibile trovare uno spanning tree valido per l'istanza {size}."))
                self.queue.put(("progress", i + 1, steps, f"Completato calcolo per {size} nodi"))

            self.queue.put(("info", "Calcoli completati con successo."))

        except Exception as e:
            self.queue.put(("error", str(e)))

    def process_queue(self):
        try:
            while not self.queue.empty():
                msg_type, *msg_data = self.queue.get_nowait()
                if msg_type == "progress":
                    self.progress_bar["value"] = msg_data[0]
                    if len(msg_data) > 1:
                        self.progress_bar["maximum"] = msg_data[1]
                    if len(msg_data) > 2:
                        self.progress_label.config(text=msg_data[2])
                elif msg_type == "info":
                    messagebox.showinfo("Completato", msg_data[0])
                elif msg_type == "error":
                    messagebox.showerror("Errore", msg_data[0])
        except Exception as e:
            messagebox.showerror("Errore", str(e))
        finally:
            self.root.after(100, self.process_queue)

    def on_closing(self):
        if self.computation_thread and self.computation_thread.is_alive():
            self.stop_event.set()
            self.computation_thread.join()
        self.root.destroy()
        os._exit(0)

# Funzione per generare un grafo casuale pesato (non completo)
def generate_random_graph(n, p, seed=None):
    G = nx.gnp_random_graph(n, p, seed=seed)
    for (u, v) in G.edges():
        G.edges[u, v]['weight'] = random.randint(1, 10)
    return G

# Funzione per generare un grafo casuale pesato e connesso
def generate_connected_random_graph(n, p, seed=None):
    attempts = 0
    while attempts < 100:  # Limite di tentativi per evitare loop infiniti
        G = nx.gnp_random_graph(n, p, seed=seed)
        if nx.is_connected(G):
            for (u, v) in G.edges():
                G.edges[u, v]['weight'] = random.randint(1, 10)
            return G
        attempts += 1
    raise ValueError(f"Impossibile generare un grafo connesso per n={n}, p={p} dopo 100 tentativi.")

# Funzione per disegnare e salvare i grafici
def draw_and_save_graph(G, filename):
    pos = nx.spring_layout(G)
    plt.figure(figsize=(8, 8))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500, font_size=10)
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    try:
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        print(f"Grafico salvato in: {filename}")
    except Exception as e:
        print(f"Errore nel salvataggio del grafico: {e}")
    plt.close()

# Funzione greedy per costruire lo spanning tree
def greedy_degree_constrained_spanning_tree(G, root, k):
    # Inizializza un grafo diretto per rappresentare lo spanning tree
    tree = nx.DiGraph()
    tree.add_node(root)
    
    # Dizionario per contare i figli di ciascun nodo
    children_count = {node: 0 for node in G.nodes()}
    
    # Insieme dei nodi già inclusi nello spanning tree
    nodes_in_tree = {root}
    
    # Continua finché tutti i nodi non sono inclusi nello spanning tree
    while len(nodes_in_tree) < len(G.nodes()):
        candidate_edge = None
        candidate_weight = float('inf')
        
        # Cerca il miglior candidato per l'aggiunta allo spanning tree
        for u in nodes_in_tree:
            # Salta i nodi che hanno già raggiunto il limite di figli
            if children_count[u] >= k:
                continue
            for v in G.neighbors(u):
                # Salta i nodi già inclusi nello spanning tree
                if v in nodes_in_tree:
                    continue
                w = G[u][v].get('weight', 1)
                # Aggiorna il candidato se trova un peso minore
                if w < candidate_weight:
                    candidate_weight = w
                    candidate_edge = (u, v)
        
        # Se non ci sono candidati validi, non è possibile costruire uno spanning tree valido
        if candidate_edge is None:
            print("Non è possibile costruire uno spanning tree che rispetti il vincolo di grado.")
            return None
        
        # Aggiungi l'arco candidato allo spanning tree
        u, v = candidate_edge
        tree.add_edge(u, v, weight=candidate_weight)
        nodes_in_tree.add(v)
        children_count[u] += 1
    
    return tree

# Funzione per calcolare il costo totale dello spanning tree
def compute_tree_cost(T):
    return sum(data.get('weight', 1) for u, v, data in T.edges(data=True))

# Funzione per verificare il vincolo di grado
def is_degree_valid(T, root, k):
    bfs_tree = nx.bfs_tree(T, root)
    children_count = {node: 0 for node in T.nodes()}
    for u, v in bfs_tree.edges():
        children_count[u] += 1
    return all(count <= k for count in children_count.values())

# Ricerca locale per migliorare lo spanning tree
def local_search_spanning_tree(G, initial_tree, root, k, max_iterations=100):
    current_tree = initial_tree.copy()  # Copia l'albero iniziale
    current_cost = compute_tree_cost(current_tree)  # Calcola il costo dell'albero corrente
    iteration = 0
    improved = True

    # Continua finché ci sono miglioramenti e non si raggiunge il numero massimo di iterazioni
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        tree_edges = list(current_tree.edges(data=True))  # Ottieni tutti gli archi dell'albero corrente

        # Prova a rimuovere ogni arco e sostituirlo con un altro per migliorare il costo
        for u, v, data in tree_edges:
            T_temp = current_tree.copy()
            T_temp.remove_edge(u, v)  # Rimuovi l'arco corrente
            components = list(nx.connected_components(T_temp))  # Trova le componenti connesse

            # Se la rimozione dell'arco non divide l'albero in due componenti, continua
            if len(components) != 2:
                continue

            comp1, comp2 = components

            # Prova a trovare un nuovo arco che collega le due componenti
            for x, y, edata in G.edges(data=True):
                if current_tree.has_edge(x, y) or current_tree.has_edge(y, x):
                    continue
                if (x in comp1 and y in comp2) or (x in comp2 and y in comp1):
                    new_tree = T_temp.copy()
                    new_tree.add_edge(x, y, weight=edata.get('weight', 1))  # Aggiungi il nuovo arco

                    # Verifica se il nuovo albero è valido e rispetta il vincolo di grado
                    if new_tree.number_of_edges() != G.number_of_nodes() - 1:
                        continue
                    if not is_degree_valid(new_tree, root, k):
                        continue

                    new_cost = compute_tree_cost(new_tree)  # Calcola il costo del nuovo albero

                    # Se il nuovo albero ha un costo inferiore, aggiorna l'albero corrente
                    if new_cost < current_cost:
                        current_tree = new_tree
                        current_cost = new_cost
                        improved = True
                        break
            if improved:
                break

    return current_tree  # Ritorna l'albero migliorato

# Simulated Annealing per migliorare lo spanning tree
def simulated_annealing_spanning_tree(G, initial_tree, root, k, initial_temp=1000, cooling_rate=0.95, iterations_per_temp=50, min_temp=1e-3):
    current_tree = initial_tree.copy()  # Copia l'albero iniziale
    current_cost = compute_tree_cost(current_tree)  # Calcola il costo dell'albero corrente
    best_tree = current_tree.copy()  # Inizializza il miglior albero come l'albero corrente
    best_cost = current_cost  # Inizializza il miglior costo come il costo corrente
    temperature = initial_temp  # Imposta la temperatura iniziale

    # Continua finché la temperatura non scende sotto il minimo
    while temperature > min_temp:
        for _ in range(iterations_per_temp):
            tree_edges = list(current_tree.edges(data=True))  # Ottieni tutti gli archi dell'albero corrente
            if not tree_edges:
                continue

            # Seleziona un arco casuale da rimuovere
            edge_to_remove = random.choice(tree_edges)
            u, v, data = edge_to_remove
            temp_tree = current_tree.copy()
            temp_tree.remove_edge(u, v)  # Rimuovi l'arco selezionato

            # Trova le componenti connesse dopo la rimozione dell'arco
            components = list(nx.connected_components(temp_tree))
            if len(components) != 2:
                continue
            comp1, comp2 = components

            # Trova tutti i possibili archi che possono collegare le due componenti
            candidate_edges = []
            for x, y, edata in G.edges(data=True):
                if current_tree.has_edge(x, y) or current_tree.has_edge(y, x):
                    continue
                if (x in comp1 and y in comp2) or (x in comp2 and y in comp1):
                    candidate_edges.append((x, y, edata.get('weight', 1)))

            if not candidate_edges:
                continue

            # Seleziona un nuovo arco casuale da aggiungere
            new_edge = random.choice(candidate_edges)
            x, y, weight_new = new_edge
            new_tree = temp_tree.copy()
            new_tree.add_edge(x, y, weight=weight_new)  # Aggiungi il nuovo arco

            # Verifica se il nuovo albero è valido e rispetta il vincolo di grado
            if new_tree.number_of_edges() != G.number_of_nodes() - 1:
                continue
            if not is_degree_valid(new_tree, root, k):
                continue

            new_cost = compute_tree_cost(new_tree)  # Calcola il costo del nuovo albero
            delta = new_cost - current_cost

            # Accetta il nuovo albero con una probabilità che dipende dalla temperatura
            if delta < 0 or random.random() < math.exp(-delta / temperature):
                current_tree = new_tree
                current_cost = new_cost
                if current_cost < best_cost:
                    best_tree = current_tree.copy()
                    best_cost = current_cost

        temperature *= cooling_rate  # Riduci la temperatura

    return best_tree  # Ritorna il miglior albero trovato

# Funzione per testare un'istanza e raccogliere metriche di performance
def test_instance(G, root, k):
    metrics = {}
    try:
        # Strategia Greedy
        start = time.time()
        greedy_tree = greedy_degree_constrained_spanning_tree(G, root, k)
        greedy_time = time.time() - start
        if greedy_tree is None:
            raise ValueError("Non è possibile costruire uno spanning tree che rispetti il vincolo di grado.")
        greedy_cost = compute_tree_cost(greedy_tree.to_undirected())
        metrics['greedy_cost'] = greedy_cost
        metrics['greedy_time'] = greedy_time
        metrics['greedy_tree'] = greedy_tree.to_undirected()

        # Ricerca Locale
        initial_tree = greedy_tree.to_undirected()
        start = time.time()
        local_tree = local_search_spanning_tree(G, initial_tree, root, k)
        local_time = time.time() - start
        local_cost = compute_tree_cost(local_tree)
        metrics['local_cost'] = local_cost
        metrics['local_time'] = local_time
        metrics['local_tree'] = local_tree

        # Simulated Annealing
        start = time.time()
        sa_tree = simulated_annealing_spanning_tree(G, initial_tree, root, k, initial_temp=1000, cooling_rate=0.95, iterations_per_temp=50)
        sa_time = time.time() - start
        sa_cost = compute_tree_cost(sa_tree)
        metrics['sa_cost'] = sa_cost
        metrics['sa_time'] = sa_time
        metrics['sa_tree'] = sa_tree

    except Exception as e:
        print(f"Errore durante il test dell'istanza: {e}")
        return None

    return metrics

# Funzione per salvare la tabella come immagine
def save_table_as_image(table_data, filename):
    df = pd.DataFrame(table_data[1:], columns=table_data[0])
    fig, ax = plt.subplots(figsize=(8, 2))  # Adegua la dimensione secondo necessità
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(df.columns))))
    try:
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        print(f"Tabella salvata in: {filename}")
    except Exception as e:
        print(f"Errore nel salvataggio della tabella: {e}")
    plt.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

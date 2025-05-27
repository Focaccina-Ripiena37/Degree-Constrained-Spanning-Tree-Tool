#app/utils.py

"""
Questo modulo contiene funzionalità di utilità per la formattazione dei colori, la validazione dell'input,
la gestione delle risorse e la manipolazione dei grafi.
"""
# Import delle librerie standard
import os
import gc
import sys
import math
import random
import logging
import threading
from functools import partial

# import delle librerie esterne
import matplotlib
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.table import Table
import matplotlib.colors as mcolors

# Configura matplotlib per utilizzare un backend non interattivo durante l'esecuzione nei thread
matplotlib.use('Agg')

# Aggiungi la directory del progetto al percorso per le importazioni
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_dir not in sys.path:
    sys.path.append(project_dir)

def validate_numeric(value, min_val=None, max_val=None):
    """
    Convalida se una stringa può essere convertita in un numero e facoltativamente controlla l'intervallo.

    Argomenti:
        valore (str): il valore stringa da convalidare
        min_val (float, opzionale): valore minimo consentito
        max_val (float, opzionale): valore massimo consentito

    Resi:
        bool: vero se valido, falso altrimenti
    """
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except ValueError:
        return False

class InputValidator:
    """
    Classe di utilità per la convalida dell'input.
    """

    @staticmethod
    def validate_numeric(value, min_val=None, max_val=None):
        """
        Convalida se una stringa può essere convertita in un numero e facoltativamente controlla l'intervallo.

        Argomenti:
            valore (str): il valore stringa da convalidare
            min_val (float, opzionale): valore minimo consentito
            max_val (float, opzionale): valore massimo consentito

        Resi:
            bool: vero se valido, falso altrimenti
        """
        return validate_numeric(value, min_val, max_val)

    @staticmethod
    def validate_integer(value, min_val=None, max_val=None):
        """
        Convalida se una stringa può essere convertita in un numero intero e facoltativamente controlla l'intervallo.

        Argomenti:
            valore (str): il valore stringa da convalidare
            min_val (int, opzionale): valore minimo consentito
            max_val (int, opzionale): valore massimo consentito

        Resi:
            bool: vero se valido, falso altrimenti
        """
        try:
            # prima controllo se è un numero valido
            if not validate_numeric(value, min_val, max_val):
                return False

            # poi controllo se è un intero
            num = float(value)
            return num.is_integer()
        except (ValueError, TypeError):
            return False


# Gestione delle risorse
class ResourceManager:
    """
    Gestisce i thread attivi e la pulizia della memoria.
    La pulizia avviene solo quando l'utente interrompe il calcolo o chiude il programma.
    """
    def __init__(self):
        self.threads = []
        self.active_computations = set()

    def add_thread(self, thread):
        """Aggiunge un nuovo thread alla gestione."""
        self.threads.append(thread)
        self.active_computations.add(thread.ident)

    def remove_thread(self, thread):
        """Rimuove un thread completato dalla gestione."""
        if thread in self.threads:
            self.threads.remove(thread)
        if thread.ident in self.active_computations:
            self.active_computations.remove(thread.ident)

    def cleanup(self):
        """Pulisce la memoria e termina i thread solo quando l'utente interrompe il calcolo o chiude il programma."""
        logging.info("Pulizia delle risorse in corso...")
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1)
        self.threads.clear()
        self.active_computations.clear()
        gc.collect()
        logging.info("Risorse liberate con successo.")


# Utility per la manipolazione dei grafi
def draw_and_save_graph(G, filename, max_children=None, is_spanning_tree=False):
    """
    Disegna il grafo e salva l'immagine, evidenziando i nodi solo se è uno spanning tree.
    - Nodo root (0) in verde (solo se spanning tree)
    - Nodi normali in blu
    - Nodi che superano il numero massimo di figli in rosso (solo se spanning tree)
    """
    if len(G.nodes()) == 0:
        print(f"⚠️ Errore: Tentativo di disegnare un grafo vuoto in {filename} ⚠️")
        return

    # Crea la cartella per i plot se non esiste
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    plot_dir = os.path.join(desktop_path, "Plot")
    os.makedirs(plot_dir, exist_ok=True)
    full_path = os.path.join(plot_dir, filename)

    # Layout per la disposizione dei nodi
    pos = nx.kamada_kawai_layout(G) if is_spanning_tree else nx.spring_layout(G, seed=42)

    # Colorazione dei nodi
    if is_spanning_tree:
        # Import della funzione centralizzata per il calcolo delle violazioni
        from .algorithms import get_violating_nodes

        violating_nodes = get_violating_nodes(G, max_children) if max_children else []

        node_colors = []
        for node in G.nodes():
            if node == 0:
                node_colors.append("#32CD32")  # Verde per il nodo root
            elif node in violating_nodes:
                node_colors.append("#FF0000")  # Rosso per nodi fuori vincolo
            else:
                node_colors.append("#3776ab")  # Blu per nodi normali
    else:
        node_colors = ["#3776ab" for _ in G.nodes()]  # Tutti blu se non è uno spanning tree

    # Disegna il grafo
    plt.figure(figsize=(8, 8))
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=800, font_size=10, edge_color='gray', width=2)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    # Salva l'immagine
    try:
        plt.savefig(full_path, bbox_inches='tight', dpi=300)
        print(f"Grafico salvato in: {full_path}")
    except Exception as e:
        print(f"Errore nel salvataggio del grafico: {e}")
    plt.close()

def save_table_as_image(table_data, filename):
    """Salva una tabella come immagine con colorazione delle celle per facilitare il confronto.
    Evidenzia automaticamente la soluzione con punteggio migliore.

    Args:
        table_data (pd.DataFrame): DataFrame da salvare come immagine.
        filename (str): Nome del file in cui salvare l'immagine.
    """
    # Verifica se il DataFrame è vuoto
    if table_data.empty or len(table_data) < 1:
        print("Errore: tabella vuota o non valida.")
        return False

    # Trova la riga con il punteggio migliore (più alto)
    best_index = None
    if "Punteggio" in table_data.columns:
        best_index = table_data["Punteggio"].idxmax()

    # Crea una figura e un asse
    fig, ax = plt.subplots(figsize=(12, 6))  # Dimensione in pollici leggermente aumentata
    ax.set_axis_off()

    # Definisci i colori per gli algoritmi (palette facilmente distinguibile)
    algo_colors = {
        "Greedy": "#D6EAF8",      # Azzurro chiaro
        "Local": "#D5F5E3",       # Verde chiaro
        "Sa": "#FAE5D3",          # Arancione chiaro
        "Simulated Annealing": "#FAE5D3"  # Stesso arancione chiaro per compatibilità
    }

    # Mappa per ricordare le istanze uniche
    instances = {}
    instance_colors = {}

    # Definisci una lista di sfumature da utilizzare per istanze diverse
    # Due sfumature per ogni colore base per evidenziare righe alternate della stessa istanza
    intensity_variants = [1.0, 0.8]  # Normale e leggermente più scuro

    # Estrai le istanze uniche e assegna un indice
    if "Istanza" in table_data.columns:
        unique_instances = table_data["Istanza"].unique()
        for idx, instance in enumerate(unique_instances):
            instances[instance] = idx

    # Crea la tabella
    table = Table(ax, bbox=[0, 0, 1, 1])

    # Stile per l'intestazione
    header_color = '#E5E8E8'  # Grigio chiaro
    header_text_color = 'black'

    # Aggiunge intestazioni di colonna
    for j, col in enumerate(table_data.columns):
        cell = table.add_cell(0, j, 1, 1, text=col, loc='center',
                              edgecolor='black', facecolor=header_color)
        cell.set_text_props(color=header_text_color, fontweight='bold')

    # Aggiunge le righe dei dati
    for i, (index, row) in enumerate(table_data.iterrows(), 1):
        # Determina il colore base in base all'algoritmo
        algo = row.get("Algoritmo", "")
        base_color = algo_colors.get(algo, "#FFFFFF")  # Bianco per algoritmi non riconosciuti

        # Evidenzia la soluzione migliore con sfondo dorato
        if best_index is not None and index == best_index:
            base_color = "#FFFACD"  # Giallo chiaro per la migliore soluzione

        # Determina l'intensità della sfumatura in base all'istanza
        instance_name = row.get("Istanza", "")
        instance_idx = instances.get(instance_name, 0)
        intensity = intensity_variants[instance_idx % len(intensity_variants)]

        # Applica l'intensità al colore base (solo se non è la soluzione migliore)
        if best_index is not None and index == best_index:
            adjusted_color = base_color  # Mantieni il colore dorato per la migliore
        else:
            rgb = mcolors.hex2color(base_color)
            adjusted_color = mcolors.rgb2hex([c * intensity for c in rgb])

        for j, col in enumerate(table_data.columns):
            value = str(row[col])

            # Distingui alcune colonne speciali per miglior leggibilità
            cell_color = adjusted_color
            text_color = 'black'
            font_weight = 'normal'

            # Evidenzia le colonne più importanti come "Costo", "Tempo" e "Punteggio"
            if col in ["Costo", "Tempo (s)", "Punteggio", "Violazioni"]:
                font_weight = 'bold'

            # Evidenzia ulteriormente la migliore soluzione
            if best_index is not None and index == best_index and col == "Punteggio":
                font_weight = 'bold'
                text_color = '#B8860B'  # Oro scuro per il punteggio della migliore soluzione

            # Aggiungi la cella con lo stile appropriato
            cell = table.add_cell(i, j, 1, 1, text=value, loc='center',
                                 edgecolor='black', facecolor=cell_color)
            cell.set_text_props(color=text_color, fontweight=font_weight)

    # Aggiungi la tabella alla figura
    ax.add_table(table)

    # Salva la figura come immagine ad alta risoluzione
    plt.savefig(filename, bbox_inches='tight', dpi=300)
    plt.close(fig)  # Chiude la figura per liberare memoria

    print(f"Tabella comparativa salvata con successo in: {filename}")
    return True

def plot_score_evolution(score_histories: dict, reference_final_values: dict = None, filename="score_evolution.png"):
    """
    Plotta l'evoluzione del punteggio nel tempo per ogni algoritmo con miglioramenti avanzati.

    Miglioramenti implementati:
    - Normalizzazione rispetto ai valori finali globali
    - Smoothing con rolling average
    - Asse Y ottimizzato per variazioni piccole
    - Annotazioni per punti chiave
    - Secondo asse per costo/violazioni (opzionale)

    Args:
        score_histories (dict): dizionario { "Algoritmo": [(iter, score_data_dict), ...] }
        reference_final_values (dict): valori finali globali per normalizzazione
        filename (str): nome file per il salvataggio
    """
    try:
        import pandas as pd
    except ImportError:
        # Fallback se pandas non è disponibile
        pd = None

    # Funzione per calcolare il punteggio normalizzato
    def evaluate_score_normalized(solution_data, reference_values):
        """Calcola il punteggio normalizzato usando valori di riferimento fissi."""
        if not reference_values:
            return solution_data.get('score', 0)  # Fallback al punteggio esistente

        def penalize(value, max_val, weight):
            if max_val == 0 or value == 0:
                return 0
            return weight * (value / max_val)

        score = 100.0
        cost_penalty = penalize(solution_data.get("cost", 0), reference_values.get("max_cost", 1), 40.0)
        viol_penalty = penalize(solution_data.get("violations", 0), reference_values.get("max_violations", 1), 30.0)
        time_penalty = penalize(solution_data.get("execution_time", 0), reference_values.get("max_time", 1), 20.0)
        memory_penalty = penalize(solution_data.get("memory", 0), reference_values.get("max_memory", 1), 10.0)

        score -= (cost_penalty + viol_penalty + time_penalty + memory_penalty)
        return max(score, 0.0)

    # Crea figura con possibilità di secondo asse
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Colori migliorati per maggiore contrasto
    colors = {
        "Simulated Annealing": "#E74C3C",  # Rosso acceso
        "Local Search": "#3498DB",         # Blu acceso
        "Greedy": "#2ECC71"                # Verde acceso
    }

    # Stili di linea per varietà visiva
    line_styles = {
        "Simulated Annealing": "-",
        "Local Search": "--",
        "Greedy": "-."
    }

    all_scores = []
    all_costs = []
    all_violations = []

    for algo, history in score_histories.items():
        if not history or len(history) == 0:
            continue

        iterations = []
        scores = []
        costs = []
        violations = []

        for item in history:
            if isinstance(item, tuple) and len(item) == 2:
                iteration, data = item

                # Gestisce sia il formato vecchio (iter, score) che nuovo (iter, score_data_dict)
                if isinstance(data, dict):
                    # Nuovo formato con dati completi
                    score = evaluate_score_normalized(data, reference_final_values)
                    cost = data.get("cost", 0)
                    violation = data.get("violations", 0)
                else:
                    # Formato vecchio (solo punteggio)
                    score = data
                    cost = 0
                    violation = 0

                iterations.append(iteration)
                scores.append(score)
                costs.append(cost)
                violations.append(violation)

                all_scores.append(score)
                all_costs.append(cost)
                all_violations.append(violation)

        if not scores:
            continue

        # Applica smoothing se pandas è disponibile
        if pd is not None and len(scores) > 3:
            smoothed_scores = pd.Series(scores).rolling(window=min(5, len(scores)), min_periods=1).mean()
            scores_to_plot = smoothed_scores.values
        else:
            scores_to_plot = scores

        color = colors.get(algo, "#333333")
        line_style = line_styles.get(algo, "-")

        # Traccia la curva principale (punteggio)
        line = ax1.plot(iterations, scores_to_plot,
                       label=f"{algo} (Punteggio)",
                       color=color,
                       linestyle=line_style,
                       linewidth=2.5,
                       marker='o' if len(iterations) <= 30 else None,
                       markersize=4,
                       alpha=0.9)

        # Aggiungi annotazioni per punti chiave
        if len(scores_to_plot) > 1:
            # Trova il primo miglioramento significativo
            for i in range(1, len(scores_to_plot)):
                if scores_to_plot[i] > scores_to_plot[0] + 1:  # Miglioramento di almeno 1 punto
                    ax1.annotate(f"Primo salto\n{algo}",
                               xy=(iterations[i], scores_to_plot[i]),
                               xytext=(iterations[i] + len(iterations)*0.1, scores_to_plot[i] + 2),
                               arrowprops=dict(arrowstyle='->', color=color, alpha=0.7),
                               fontsize=9, ha='center',
                               bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
                    break

            # Trova il punto di massimo
            max_idx = scores_to_plot.argmax() if hasattr(scores_to_plot, 'argmax') else scores.index(max(scores))
            if max_idx > 0 and max_idx < len(iterations) - 1:
                ax1.annotate(f"Max: {scores_to_plot[max_idx]:.1f}",
                           xy=(iterations[max_idx], scores_to_plot[max_idx]),
                           xytext=(iterations[max_idx], scores_to_plot[max_idx] + 1),
                           ha='center', fontsize=8,
                           bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.3))

    # Configurazione asse principale (punteggio)
    ax1.set_xlabel("Iterazione", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Punteggio Normalizzato (più alto = migliore)", fontsize=12, fontweight='bold', color='black')
    ax1.tick_params(axis='y', labelcolor='black')

    # Ottimizza l'asse Y per rendere visibili variazioni piccole
    if all_scores:
        min_score = min(all_scores)
        max_score = max(all_scores)
        score_range = max_score - min_score

        if score_range < 5:  # Se la variazione è piccola, espandi la vista
            margin = max(2, score_range * 0.2)
            ax1.set_ylim(min_score - margin, max_score + margin)
        else:
            margin = score_range * 0.1
            ax1.set_ylim(min_score - margin, max_score + margin)

    # Secondo asse per costo (opzionale, se ci sono dati di costo)
    if all_costs and any(c > 0 for c in all_costs):
        ax2 = ax1.twinx()

        for algo, history in score_histories.items():
            if not history:
                continue

            iterations = []
            costs = []

            for item in history:
                if isinstance(item, tuple) and len(item) == 2:
                    iteration, data = item
                    if isinstance(data, dict):
                        iterations.append(iteration)
                        costs.append(data.get("cost", 0))

            if costs and any(c > 0 for c in costs):
                color = colors.get(algo, "#333333")
                ax2.plot(iterations, costs,
                        color=color,
                        linestyle=':',
                        alpha=0.5,
                        linewidth=1.5,
                        label=f"{algo} (Costo)")

        ax2.set_ylabel("Costo", fontsize=10, color='gray')
        ax2.tick_params(axis='y', labelcolor='gray')

    # Titolo e griglia
    plt.title("Evoluzione del Punteggio durante l'Esecuzione degli Algoritmi\n(con Normalizzazione e Smoothing)",
              fontsize=14, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax1.legend(fontsize=10, loc='upper left')

    # Migliora l'aspetto del grafico
    plt.tight_layout()

    # Crea la cartella Plot se non esiste
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    plot_dir = os.path.join(desktop_path, "Plot")
    os.makedirs(plot_dir, exist_ok=True)
    full_path = os.path.join(plot_dir, filename)

    try:
        plt.savefig(full_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close()
        print(f"✅ Grafico evoluzione migliorato salvato: {full_path}")
        return True
    except Exception as e:
        print(f"❌ Errore nel salvataggio del grafico evoluzione: {e}")
        plt.close()
        return False

def generate_connected_random_graph(n, p=0.3):
    """
    Genera un grafo pesato non completo con n nodi e probabilità di connessione p.
    Garantisce che il grafo sia connesso e contenga un cammino hamiltoniano.
    """
    logging.info(f"Generazione del grafo con {n} nodi e p={p}")
    while True:
        G = nx.erdos_renyi_graph(n, p)
        if not nx.is_connected(G):
            continue  # Rigenera il grafo se non è connesso

        # Rinomina i nodi in ordine casuale
        mapping = {old: new for new, old in enumerate(random.sample(list(G.nodes()), len(G.nodes())))}
        G = nx.relabel_nodes(G, mapping)

        # Assegna pesi casuali agli archi
        for u, v in G.edges():
            G[u][v]['weight'] = random.randint(1, 10)

        # Verifica e garantisce il cammino hamiltoniano
        if ensure_hamiltonian_path(G):
            return G

def ensure_hamiltonian_path(G):
    """
    Verifica e garantisce che il grafo abbia un cammino hamiltoniano.
    Se non esiste, aggiunge archi strategicamente.
    """
    def dfs_hamiltonian_iterative(start_node):
        stack = [(start_node, {start_node}, [start_node])]
        while stack:
            node, visited, path = stack.pop()
            if len(path) == len(G):
                return path
            neighbors = sorted(G.neighbors(node), key=lambda x: G[node][x]['weight'])
            for neighbor in neighbors:
                if neighbor not in visited:
                    new_visited = visited | {neighbor}
                    new_path = path + [neighbor]
                    stack.append((neighbor, new_visited, new_path))
        return None

    # Prova a trovare un cammino hamiltoniano
    if dfs_hamiltonian_iterative(0):
        return True

    # Se non trovato, aggiunge archi random tra nodi non connessi e riprova
    for _ in range(len(G)):
        unconnected_nodes = [(u, v) for u in G.nodes() for v in G.nodes() if u != v and not G.has_edge(u, v)]
        if unconnected_nodes:
            u, v = random.choice(unconnected_nodes)
            G.add_edge(u, v, weight=random.randint(1, 10))

        if dfs_hamiltonian_iterative(0):
            return True

    return False
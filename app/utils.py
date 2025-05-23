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
        node_colors = []
        for node in G.nodes():
            if node == 0:
                node_colors.append("#32CD32")  # Verde per il nodo root
            elif max_children and len([child for child in G.neighbors(node) if G.degree(child) < G.degree(node)]) > max_children:
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
    
    Args:
        table_data (pd.DataFrame): DataFrame da salvare come immagine.
        filename (str): Nome del file in cui salvare l'immagine.
    """
    # Verifica se il DataFrame è vuoto
    if table_data.empty or len(table_data) < 1:
        print("Errore: tabella vuota o non valida.")
        return False
    
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
        
        # Determina l'intensità della sfumatura in base all'istanza
        instance_name = row.get("Istanza", "")
        instance_idx = instances.get(instance_name, 0)
        intensity = intensity_variants[instance_idx % len(intensity_variants)]
        
        # Applica l'intensità al colore base
        rgb = mcolors.hex2color(base_color)
        adjusted_color = mcolors.rgb2hex([c * intensity for c in rgb])
        
        for j, col in enumerate(table_data.columns):
            value = str(row[col])
            
            # Distingui alcune colonne speciali per miglior leggibilità
            cell_color = adjusted_color
            text_color = 'black'
            font_weight = 'normal'
            
            # Evidenzia le colonne più importanti come "Costo" e "Tempo"
            if col in ["Costo", "Tempo (s)"]:
                font_weight = 'bold'
            
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
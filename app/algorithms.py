# app/algorithms.py - Algoritmi principali per l'applicazione DCST

#==============================================================================
#                           1. IMPORTAZIONI
#==============================================================================

# Importazioni della libreria standard
import os
import gc
import sys
import math
import time
import random
import logging
import functools
import tracemalloc
from collections import deque
from typing import List, Tuple, Dict, Any, Optional

# Importazioni di terze parti
import heapq
import psutil
import numpy as np
import pandas as pd
import networkx as nx
import concurrent.futures
from functools import partial
from memory_profiler import memory_usage

#==============================================================================
#                           2. DEFINIZIONE DELLE VARIABILI GLOBALI
#==============================================================================
greedy_cost_calls = [0]
local_search_cost_calls = [0]
sa_cost_calls = [0]

#==============================================================================
#                           3. INIZIALIZZAZIONE DELL'ISTANZA DI TEST
#==============================================================================
test_instance = {
    'graph': nx.Graph(),
    'red_nodes': [],
    'weights': {}
}

def initialize_test_instance():
    """Initialize a test graph instance with sample data"""
    G = nx.Graph()
    # Aggiungi nodi
    nodes = range(1, 6)
    for node in nodes:
        G.add_node(node)

    # Aggiungi archi con pesi
    edges_with_weights = [
        (1, 2, 10), (1, 3, 15), (2, 3, 5),
        (2, 4, 8), (3, 4, 12), (3, 5, 20), (4, 5, 7)
    ]

    for u, v, w in edges_with_weights:
        G.add_edge(u, v, weight=w)

    # Definisci i nodi rossi (con vincoli)
    red_nodes = [1, 5]

    # Aggiorna l'istanza di test
    test_instance['graph'] = G
    test_instance['red_nodes'] = red_nodes
    test_instance['weights'] = {(u, v): w for u, v, w in edges_with_weights}

    logging.info("Test instance initialized successfully")
    return test_instance

initialize_test_instance()

#==============================================================================
#                           4. FUNZIONI UNITARIE DI BASE
#==============================================================================
def calculate_cost_base(spanning_tree, max_children, penalty, counter):
    """
    Calcola il costo di un albero di copertura e aggiorna il contatore di chiamate.

    Args:
        spanning_tree: Grafo che rappresenta l'albero di copertura
        max_children: Numero massimo di figli per nodo
        penalty: Penalità per violazione dei vincoli
        counter: Lista contenente il contatore per le chiamate della funzione

    Returns:
        total_cost: Costo totale dell'albero
    """
    counter[0] += 1  # Incrementa il contatore associato all'algoritmo

    total_cost = sum(spanning_tree.edges[edge]['weight'] for edge in spanning_tree.edges())

    for node in spanning_tree.nodes():
        children = [child for child in spanning_tree.neighbors(node) if spanning_tree.degree(child) < spanning_tree.degree(node)]
        if len(children) > max_children:
            total_cost += penalty * (len(children) - max_children)

    return total_cost

# Usa la function.partial per creare versioni specifiche per ogni algoritmo
calculate_cost_greedy = partial(calculate_cost_base, counter=greedy_cost_calls)
calculate_cost_local = partial(calculate_cost_base, counter=local_search_cost_calls)
calculate_cost_sa = partial(calculate_cost_base, counter=sa_cost_calls)

def validate_solution(graph, solution):
    """Validate that a solution forms a valid spanning tree"""
    edges = solution['edges']

    # Crea un grafo da soluzione
    solution_graph = nx.Graph()
    solution_graph.add_nodes_from(graph.nodes())
    solution_graph.add_edges_from(edges)

    # Controlla se l'albero è connesso e senza cicli
    is_connected = nx.is_connected(solution_graph)
    is_tree = is_connected and len(edges) == len(graph.nodes()) - 1

    return is_tree

def evaluate_solution(solution: Dict[str, Any], constraints: Dict[str, Any]) -> float:
    """
    Valutare la qualità di una soluzione.

    Questa è una funzione segnaposto: implementala in base ai tuoi obiettivi di ottimizzazione specifici.
    """
    score = 0.0
    # Implementa qui la logica di valutazione della soluzione
    # Un punteggio più alto indica una soluzione migliore

    # Esempio: valutazione in base all'efficienza dell'utilizzo della memoria
    if "memory_usage" in solution and "target_memory" in constraints:
        efficiency = min(solution["memory_usage"] / constraints["target_memory"], 1.0)
        score += efficiency * 100

    return score

def is_dcst(_, tree_edges, degree_constraints):
    """
    Controlla se il dato insieme di bordi forma un albero ricoprente con vincoli di grado (DCST) valido.

    Parametri:
    - grafico: la rappresentazione grafica completa (nodi e tutti i possibili spigoli)
    - tree_edges: elenco di bordi che formano il potenziale DCST
    - Degree_constraints: dizionario che mappa i nodi al loro grado massimo consentito

    Resi:
    - bool: Vero se l'albero è un DCST valido, Falso altrimenti
    """
    # Controlla se forma un albero (connesso e senza cicli)
    nodes = set()
    for edge in tree_edges:
        u, v = edge[0], edge[1]
        nodes.add(u)
        nodes.add(v)

    # Un albero con n nodi deve avere esattamente n-1 spigoli
    if len(tree_edges) != len(nodes) - 1:
        return False

    # Controlla se l'albero è connesso
    # Utilizzo di DFS semplice per verificare la connettività
    visited = set()
    if nodes:
        start_node = next(iter(nodes))

        # Costruisce la lista delle adiacenze per l'albero
        adjacency = {node: [] for node in nodes}
        for u, v in tree_edges:
            adjacency[u].append(v)
            adjacency[v].append(u)

        def dfs(node):
            visited.add(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    dfs(neighbor)

        dfs(start_node)

        if len(visited) != len(nodes):
            return False

    # Controlla i vincoli di grado
    node_degrees = {node: 0 for node in nodes}
    for u, v in tree_edges:
        node_degrees[u] += 1
        node_degrees[v] += 1

    for node, degree in node_degrees.items():
        if node in degree_constraints and degree > degree_constraints[node]:
            return False

    return True

def _ensure_spanning(G, T):
    """
    Garantisce che l'albero si estenda su tutti i nodi del grafico aggiungendo bordi di peso minimo.
    """
    # Aggiungi tutti i nodi da G a T se non sono già presenti
    for node in G.nodes():
        if node not in T.nodes():
            T.add_node(node)

    # Assicurati che l'albero sia connesso
    components = list(nx.connected_components(T))

    while len(components) > 1:
        min_edge = None
        min_weight = float('inf')

        # Trova l'arco di peso minimo tra i componenti connessi
        for comp1_idx in range(len(components)):
            for comp2_idx in range(comp1_idx + 1, len(components)):
                comp1 = components[comp1_idx]
                comp2 = components[comp2_idx]

                for u in comp1:
                    for v in comp2:
                        if G.has_edge(u, v):
                            weight = G.edges[u, v]['weight']
                            if weight < min_weight:
                                min_weight = weight
                                min_edge = (u, v)

        # Aggiungi l'arco minimo all'albero
        if min_edge:
            T.add_edge(min_edge[0], min_edge[1], weight=G.edges[min_edge]['weight'])
        else:
            # Nessun arco trovato, interrompi
            break

        # Ricalcola i componenti connessi
        components = list(nx.connected_components(T))

    return T

#==============================================================================
#                           5. ALGORITMI PRINCIPALI
#==============================================================================

def greedy_spanning_tree(G, max_children=float('inf'), penalty=1000):
    """
    Genera un albero di copertura usando un algoritmo greedy modificato.

    Parameters:
    - G: Grafo da cui generare l'albero
    - max_children: Limite superiore per il numero di figli dei nodi nell'albero
    - penalty: Penalizzazione per le aree che violano il limite di figli

    Returns:
    - T: Albero di copertura generato
    """
    global greedy_cost_calls
    greedy_cost_calls[0] += 1

    if not G:
        return nx.Graph()

    # Inizializza un albero vuoto e traccia i gradi dei nodi
    T = nx.Graph()
    T.add_nodes_from(G.nodes())
    children_count = {node: 0 for node in G.nodes()}

    # Inizia con un nodo casuale (o il primo)
    nodes = list(G.nodes())
    start_node = nodes[0]

    # Tieni traccia dei bordi da considerare
    candidate_edges = []
    visited = {start_node}

    # Aggiungi tutti i bordi dal nodo iniziale all'elenco dei candidati
    for neighbor, edge_data in G[start_node].items():
        weight = edge_data.get('weight', 1)
        heapq.heappush(candidate_edges, (weight, start_node, neighbor))

    # Fai crescere l'albero usando l'algoritmo di Prim modificato
    while candidate_edges and len(visited) < len(G.nodes()):
        weight, u, v = heapq.heappop(candidate_edges)

        # Salta se entrambi i nodi sono già nell'albero
        if v in visited:
            continue

        # Controlla se aggiungere l'arco viola i vincoli sui figli
        children_u = [child for child in T.neighbors(u) if T.degree(child) < T.degree(u)]
        children_v = [child for child in T.neighbors(v) if T.degree(child) < T.degree(v)]

        if len(children_u) < max_children and len(children_v) < max_children:
            # Aggiungi l'arco all'albero
            T.add_edge(u, v, weight=G[u][v].get('weight', 1))
            children_count[u] += 1
            children_count[v] += 1
            visited.add(v)

            # Aggiungi un nuovo nodo ai candidati
            for neighbor, edge_data in G[v].items():
                if neighbor not in visited:
                    weight = edge_data.get('weight', 1)
                    heapq.heappush(candidate_edges, (weight, v, neighbor))

    # Calcola il costo totale utilizzando la funzione calcola_costo aggiornata
    total_cost = calculate_cost_greedy(T, max_children, penalty)
    return T, total_cost

def adaptive_neighborhood_local_search(G, initial_tree, max_children, penalty, max_iterations=5000, stop_event=None, queue=None, callback=None):
    current_tree = initial_tree.copy()
    best_tree = current_tree.copy()
    best_cost = calculate_cost_local(best_tree, max_children, penalty)

    # Imposta la dimensione iniziale del quartiere
    neighborhood_size = 1
    iterations_without_improvement = 0

    cost_calls = local_search_cost_calls[0]  # Manteniamo il valore del contatore

    # Inizializza lo storico dei punteggi per il grafico temporale
    score_history = []
    start_time = time.time()

    for iteration in range(max_iterations):
        if stop_event and stop_event.is_set():
            break

        # Aggiorna la GUI se la coda esiste
        if queue and iteration % 10 == 0:
            queue.put(("iter", f"{iteration}/{max_iterations}"))
            queue.put(("cost", best_cost))

        # Se viene fornita una richiamata, utilizzala per segnalare l'avanzamento
        if callback:
            improved = False
            if iteration % 5 == 0:  # Report ogni 5 iterazioni
                message = f"Iteration {iteration}/{max_iterations}"
                callback(message, best_cost, queue=queue, improved=improved)

        # Raccoglie dati dettagliati ogni 5 iterazioni per il grafico temporale
        if iteration % 5 == 0:
            violations = count_constraint_violations(current_tree, max_children)
            current_time = time.time() - start_time
            current_cost = calculate_cost_local(current_tree, max_children, penalty)

            # Salva dati completi per normalizzazione successiva
            score_data = {
                "cost": current_cost,
                "execution_time": current_time,
                "memory": 0,  # Placeholder per la memoria
                "violations": violations
            }
            score_history.append((iteration, score_data))

        # Trova i nodi che violano i vincoli di grado
        constrained_nodes = get_violating_nodes(current_tree, max_children)

        if not constrained_nodes:
            # Se nessun vincolo viene violato, prova gli scambi casuali per migliorare i costi
            improvement_made = try_random_edge_swap(G, current_tree, max_children, penalty, neighborhood_size)
            cost_calls += neighborhood_size * 2  # Ogni tentativo di scambio valuta almeno 2 stati, moltiplicato per neighborhood_size
            if not improvement_made:
                iterations_without_improvement += 1
            else:
                iterations_without_improvement = 0
                if callback:
                    callback(iteration, best_cost, queue=queue, improved=True)
        else:
            # Prova a correggere le violazioni dei vincoli con tentativi multipli
            improvement_made = fix_constraint_violations(G, current_tree, constrained_nodes, max_children, penalty, neighborhood_size)
            cost_calls += neighborhood_size * len(constrained_nodes) * 2  # Ogni tentativo per nodo valuta almeno 2 stati
            if not improvement_made:
                iterations_without_improvement += 1
            else:
                iterations_without_improvement = 0

        # Calcola il costo attuale
        current_cost = calculate_cost_local(current_tree, max_children, penalty)
        cost_calls += 1

        # Aggiorna la soluzione migliore se migliore
        if current_cost < best_cost:
            best_tree = current_tree.copy()
            best_cost = current_cost
            iterations_without_improvement = 0
            if callback:
                callback(iteration, best_cost, queue=queue, improved=True)

        # Adattare le dimensioni del quartiere in base ai progressi
        if iterations_without_improvement > 10:
            neighborhood_size = min(neighborhood_size + 1, 5)  # Incrementa gradualmente fino a 5 nodi
        elif iterations_without_improvement > 20:
            # Se bloccato, prova a ridurre le dimensioni dell'intorno
            current_tree = best_tree.copy()
            neighborhood_size = 1
            iterations_without_improvement = 0

        # Condizione di arresto anticipato
        if iterations_without_improvement > 30:
            break

    # Report finale
    if queue:
        queue.put(("log", (f"Local Search completata: {iteration+1} iterazioni, {cost_calls} chiamate alla funzione di costo", "info")))

    local_search_cost_calls[0] = cost_calls

    return best_tree, cost_calls, score_history

def simulated_annealing_spanning_tree(G, max_children=3, penalty=1000, max_iterations=10000, initial_temperature=200, cooling_rate=0.98, stop_event=None, queue=None, return_stats=False, initial_tree=None, progress_callback=None):
    """
    Algoritmo avanzato di Simulated Annealing per trovare spanning tree ottimali con vincoli di grado.
    Utilizza il raffreddamento e il riscaldamento adattivi e una strategia migliorata di generazione dei vicini per trovare soluzioni migliori.

    Argomenti:
        G (networkx.Graph): il grafico di input
        max_children (int): numero massimo consentito di figli per qualsiasi nodo
        penalità (int): valore di penalità per ogni violazione del vincolo figlio
        max_iterations (int): numero massimo di iterazioni
        temperatura_iniziale (float): temperatura iniziale
        cooling_rate (float): velocità alla quale la temperatura diminuisce
        stop_event (threading.Event): evento per segnalare l'arresto dell'algoritmo
        coda (queue.Queue): coda per la comunicazione con la GUI
        return_stats (bool): se restituire statistiche dettagliate
        partial_tree (networkx.Graph): albero iniziale da cui partire (idealmente dalla ricerca locale adattiva)

    Resi:
        tuple o networkx.Graph: lo spanning tree risultante e facoltativamente le statistiche
    """

    global sa_cost_calls
    sa_cost_calls[0] += 1

    # Inizia con l'albero iniziale, se fornito, altrimenti utilizza un approccio di base
    if initial_tree is not None:
        T = initial_tree.copy()
        if queue:
            queue.put(("log", (f"Iniziando SA dall'albero ottimizzato da Local Search", "info")))
    else:
        # Se non viene fornito alcun albero iniziale, creane uno con l'ottimizzazione di base
        if hasattr(nx, 'algorithms') and hasattr(nx.algorithms, 'approximation') and hasattr(nx.algorithms.approximation, 'steinertree'):
            # Se disponibile, prova a utilizzare l'approssimazione dell'albero di Steiner come punto di partenza
            try:
                # Utilizzare un sottoinsieme di nodi come terminali per approssimare un buon spanning tree
                terminals = random.sample(list(G.nodes()), max(3, len(G.nodes()) // 5))
                T = nx.algorithms.approximation.steinertree.steiner_tree(G, terminals)
                # Add any missing nodes
                for node in G.nodes():
                    if node not in T.nodes():
                        T.add_node(node)
                # Assicura che sia un albero di copertura aggiungendo bordi di peso minimo
                T = _ensure_spanning(G, T)
            except:
                # Ritorna al MST se l'albero di Steiner fallisce
                T = nx.minimum_spanning_tree(G)
        else:
            # Se l'algoritmo specializzato non è disponibile, utilizzare MST con ricerca locale adattiva
            T = nx.minimum_spanning_tree(G)

        # Applicare un rapido miglioramento locale alla soluzione iniziale se non è stato fornito alcun albero iniziale
        for _ in range(10):  # Limita le iterazioni per evitare tempi di esecuzione eccessivi
            T = _improve_tree_locally(G, T, max_children, penalty)

    # Calcola le chimate alla funzione di costo iniziale
    cost = calculate_cost_sa(T, max_children, penalty)
    sa_cost_calls[0] += 1
    best_cost = cost
    best_tree = T.copy()

    # Parametri di ricottura simulata migliorati
    temperature = initial_temperature
    min_temperature = 0.01  # Temperatura minima prima di considerare il riscaldamento
    iteration = 0
    accepted_count = 0
    rejected_count = 0
    plateau_count = 0

    # Parametri per il raffreddamento adattivo
    alpha = cooling_rate  # Velocità di raffreddamento iniziale
    adaptive_cooling = True

    # Parametri di riscaldamento
    reheating_factor = 1.5
    max_reheats = 3
    reheat_count = 0

    # Parametri multi-stadio per adattare i parametri in base all'iterazione
    stage = 1
    stage_lengths = {
        1: max_iterations // 3,       # Exploration stage (high temperature)
        2: max_iterations // 3,       # Transition stage (medium temperature)
        3: max_iterations // 3        # Exploitation stage (low temperature)
    }
    stage_cooling_rates = {
        1: cooling_rate,              # Normal cooling in exploration
        2: cooling_rate * 0.98,       # Slower cooling in transition
        3: cooling_rate * 0.95        # Even slower cooling in exploitation
    }

    # Cronologia delle soluzioni per il rilevamento dei plateau
    cost_history = []
    best_cost_history = []

    # Inizializza lo storico dei punteggi per il grafico temporale
    score_history = []
    start_time = time.time()

    while temperature > min_temperature and iteration < max_iterations:
        # Controlla se l'algoritmo deve essere interrotto
        if stop_event and stop_event.is_set():
            break

        # Aggiorna la GUI periodicamente data la coda
        if queue and iteration % 10 == 0:
            queue.put(("temperature", round(temperature, 2)))
            queue.put(("iteration", iteration))
            queue.put(("cost", cost))
            queue.put(("accepted", accepted_count))
            queue.put(("plateau", plateau_count))
            queue.put(("reheats", reheat_count))

        # Raccoglie dati dettagliati ogni 10 iterazioni per il grafico temporale
        if iteration % 10 == 0:
            violations = count_constraint_violations(T, max_children)
            current_time = time.time() - start_time

            # Salva dati completi per normalizzazione successiva
            score_data = {
                "cost": cost,
                "execution_time": current_time,
                "memory": 0,  # Placeholder per la memoria
                "violations": violations
            }
            score_history.append((iteration, score_data))

        # Determinare la fase corrente in base al conteggio delle iterazioni
        current_iter_stage = 1
        iter_count = 0
        for s, length in stage_lengths.items():
            iter_count += length
            if iteration < iter_count:
                current_iter_stage = s
                break

        # Regola i parametri in base alla fase corrente
        if current_iter_stage != stage:
            stage = current_iter_stage
            alpha = stage_cooling_rates[stage]

        # Genera una soluzione vicina di qualità superiore utilizzando una strategia avanzata
        neighbor_tree = T.copy()

        # Scegli probabilisticamente la strategia di generazione dei vicini in base alla temperatura
        # A temperature elevate, dare priorità all'esplorazione; a basse temperature, privilegiare lo sfruttamento
        strategy_prob = temperature / initial_temperature

        if random.random() < strategy_prob:
            # Exploration strategy: more random changes
            generate_neighbor_tree(G, neighbor_tree, max_children, penalty)
        else:
            # Exploitation strategy: more focused changes
            _generate_targeted_neighbor(G, neighbor_tree, max_children, penalty)

        # Calculate new cost
        neighbor_cost = calculate_cost_sa(neighbor_tree, max_children, penalty)
        sa_cost_calls[0] += 1  # Update counter

        # Decide whether to accept the new solution with enhanced criteria
        delta_cost = neighbor_cost - cost

        # Accept with probability based on Metropolis criterion with quality awareness
        # For equal or better solutions, always accept
        # For worse solutions, acceptance probability depends on how much worse and temperature
        acceptance_prob = math.exp(-delta_cost / temperature) if delta_cost > 0 else 1.0

        # At very low temperatures, also consider degree constraint violations more heavily
        if temperature < 1.0:
            # Count constraint violations in both current and neighbor
            current_violations = count_constraint_violations(T, max_children)
            neighbor_violations = count_constraint_violations(neighbor_tree, max_children)

            # Adjust acceptance probability based on violation changes
            if neighbor_violations > current_violations:
                acceptance_prob *= 0.5  # Penalize increases in violations at low temps
            elif neighbor_violations < current_violations:
                acceptance_prob = min(acceptance_prob * 2.0, 1.0)  # Favor decreases

        if random.random() < acceptance_prob:
            T = neighbor_tree
            cost = neighbor_cost
            accepted_count += 1

            # Track best solution
            if cost < best_cost:
                best_cost = cost
                best_tree = T.copy()
                plateau_count = 0
            else:
                plateau_count += 1
        else:
            rejected_count += 1
            plateau_count += 1

        # Track cost history for plateau detection
        cost_history.append(cost)
        best_cost_history.append(best_cost)
        if len(cost_history) > 100:  # Keep history limited
            cost_history.pop(0)
            best_cost_history.pop(0)

        # Adaptive cooling rate based on acceptance rate
        if adaptive_cooling and iteration % 100 == 0 and iteration > 0:
            recent_acceptance_rate = accepted_count / (accepted_count + rejected_count)

            # Reset counters for next period
            accepted_count = 0
            rejected_count = 0

            # Adjust cooling rate based on acceptance rate
            if recent_acceptance_rate > 0.6:  # Too many acceptances - cool faster
                alpha = min(alpha * 1.05, 0.99)
            elif recent_acceptance_rate < 0.2:  # Too few acceptances - cool slower
                alpha = max(alpha * 0.95, 0.8)

        # Consider reheating if stuck in a plateau
        if plateau_count > 200 and reheat_count < max_reheats:
            # Check if we're in a true plateau by analyzing cost history variance
            if len(cost_history) > 50:
                recent_costs = cost_history[-50:]
                cost_variance = np.var(recent_costs) if hasattr(np, 'var') else sum((c - sum(recent_costs)/len(recent_costs))**2 for c in recent_costs)/len(recent_costs)

                if cost_variance < 0.001 * best_cost:  # Very small variance indicates a plateau
                    # Reheat the system
                    temperature = min(temperature * reheating_factor, initial_temperature * 0.5)
                    reheat_count += 1
                    plateau_count = 0

                    # Log reheating event
                    if queue:
                        queue.put(("log", (f"Reheating applied (#{reheat_count}): New temperature = {temperature:.2f}", "highlight")))

        # Log plateau and reheat status periodically
        if queue and iteration % 100 == 0:
            queue.put(("log", (f"[SA] Plateau: {plateau_count} – Reheat: {reheat_count}", "info")))

        # Cool down the temperature using current adaptive rate
        temperature *= alpha
        iteration += 1

        # Update progress callback
        if progress_callback:
            progress_callback(iteration, temperature, cost, accepted_count, max_iterations)

        # Every 500 iterations, perform a focused improvement on the current best solution
        if iteration % 500 == 0:
            improved_best = best_tree.copy()
            improved_best = _improve_tree_locally(G, improved_best, max_children, penalty)
            improved_cost = calculate_cost_sa(improved_best, max_children, penalty)

            if improved_cost < best_cost:
                best_tree = improved_best.copy()
                best_cost = improved_cost
                if queue:
                    queue.put(("log", (f"Focused improvement found better solution: {best_cost}", "success")))

    # Final intensification phase: try to improve the best solution one more time
    final_best = best_tree.copy()
    final_best = _improve_best_solution(G, final_best, max_children, penalty)
    final_cost = calculate_cost_sa(final_best, max_children, penalty)
    sa_cost_calls[0] += 1  # Update counter

    if final_cost < best_cost:
        best_tree = final_best
        best_cost = final_cost
        if queue:
            queue.put(("log", (f"Final intensification improved solution to: {best_cost}", "success")))

    if return_stats:
        stats = {
            "iterations": iteration,
            "accepted_moves": accepted_count + rejected_count,  # Total moves
            "rejected_moves": rejected_count,
            "final_cost": best_cost,
            "final_temperature": temperature,
            "reheats_applied": reheat_count
        }
        sa_cost_calls[0] = iteration  # Use the total number of iterations to reflect the calls
        return best_tree, stats, score_history
    else:
        sa_cost_calls[0] = iteration  # Use the total number of iterations to reflect the calls
        return best_tree, best_cost, iteration, accepted_count, score_history

#==============================================================================
#                           6. FUNZIONI DI SUPPORTO
#==============================================================================
def generate_neighbor_tree(G, tree, max_children, penalty):
    """
    Generates a neighboring solution for simulated annealing.

    Args:
        G: Original graph
        tree: Current spanning tree
        max_children: Maximum allowed number of children
        penalty: Penalty for violations

    Returns:
        new_tree: A neighboring spanning tree
    """
    # Choose a random edge to remove
    edge_to_remove = random.choice(list(tree.edges()))
    u, v = edge_to_remove

    # Remove the edge
    tree.remove_edge(u, v)

    # Find the two components
    components = list(nx.connected_components(tree))

    if len(components) == 1:
        # The removal didn't disconnect the tree, add the edge back and try again
        tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return generate_neighbor_tree(G, tree, max_children, penalty)

    # Find a new edge to connect the components
    component1 = components[0]
    component2 = components[1]

    # Find all potential edges between the components from the original graph
    potential_edges = []
    for node1 in component1:
        for node2 in component2:
            if G.has_edge(node1, node2):
                # Calculate the effective weight considering potential child violations
                new_children1 = len([child for child in tree.neighbors(node1) if tree.degree(child) < tree.degree(node1)]) + 1
                new_children2 = len([child for child in tree.neighbors(node2) if tree.degree(child) < tree.degree(node2)]) + 1

                child_penalty = max(0, new_children1 - max_children) + max(0, new_children2 - max_children)
                effective_weight = G.edges[node1, node2]['weight'] + (child_penalty * penalty * 0.1)

                potential_edges.append((node1, node2, effective_weight))

    # If no potential edges found, revert and try again
    if not potential_edges:
        tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return generate_neighbor_tree(G, tree, max_children, penalty)

    # Choose an edge based on weights (prefer lower weights)
    potential_edges.sort(key=lambda x: x[2])

    # Probabilistically select an edge, favoring lower weights
    weights = [1.0/(1.0+e[2]) for e in potential_edges]
    total = sum(weights)
    weights = [w/total for w in weights]

    chosen_edge = random.choices(potential_edges, weights=weights)[0]
    node1, node2, _ = chosen_edge

    # Add the new edge to reconnect the tree
    tree.add_edge(node1, node2, weight=G.edges[node1, node2]['weight'])

    return tree

def _generate_targeted_neighbor(G, tree, max_children, penalty):
    """
    Generates a targeted neighboring solution based on current constraints and cost analysis.
    Prefers modifications that address child constraint violations or high-cost edges.
    """
    # Check for child constraint violations
    constrained_nodes = get_violating_nodes(tree, max_children)

    if constrained_nodes and random.random() < 0.7:  # 70% chance to focus on fixing constraints
        # Pick a constrained node
        node = random.choice(constrained_nodes)

        # Get edges from this node sorted by weight (descending)
        edges = [(node, neighbor, tree.edges[node, neighbor]['weight'])
                for neighbor in tree.neighbors(node)]
        edges.sort(key=lambda x: -x[2])  # Sort by weight, highest first

        # Try to replace a high-weight edge
        for u, v, _ in edges[:2]:  # Focus on the two highest-weight edges
            # Remove this edge
            tree.remove_edge(u, v)

            # Check if tree is still connected
            if not nx.is_connected(tree):
                # Find components
                components = list(nx.connected_components(tree))
                comp1 = [c for c in components if u in c][0]
                comp2 = [c for c in components if v in c][0]

                # Find alternative connections that don't involve the constrained node
                alt_edges = []
                for n1 in comp1:
                    if n1 == node:
                        continue  # Skip the constrained node
                    for n2 in comp2:
                        if G.has_edge(n1, n2):
                            weight = G.edges[n1, n2]['weight']
                            alt_edges.append((n1, n2, weight))

                if alt_edges:
                    # Sort by weight
                    alt_edges.sort(key=lambda x: x[2])

                    # Pick one of the best alternatives with some randomness
                    idx = min(int(random.expovariate(1) * len(alt_edges)), len(alt_edges) - 1)
                    n1, n2, _ = alt_edges[idx]
                    tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])
                    return tree  # Successfully modified
                else:
                    # No alternative found, put back the original edge
                    tree.add_edge(u, v, weight=G.edges[u, v]['weight'])

    # If we get here, either there are no constraint violations or we couldn't fix them
    # Try a standard edge swap but with more focus on high-cost edges

    # Find high-cost edges in the tree
    edges = [(u, v, tree.edges[u, v]['weight']) for u, v in tree.edges()]
    edges.sort(key=lambda x: -x[2])  # Sort by weight, highest first

    # Try to replace one of the highest-cost edges
    edge_idx = min(int(random.expovariate(0.5) * len(edges)), len(edges) - 1)
    u, v, _ = edges[edge_idx]

    # Remove this edge
    tree.remove_edge(u, v)

    # Standard reconnection logic similar to generate_neighbor_tree
    components = list(nx.connected_components(tree))

    if len(components) == 1:
        # The edge didn't disconnect the tree (shouldn't happen in a proper tree)
        tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return generate_neighbor_tree(G, tree, max_children, penalty)

    # Find a new edge to connect components
    comp1, comp2 = components[0], components[1]

    potential_edges = []
    for n1 in comp1:
        for n2 in comp2:
            if G.has_edge(n1, n2) and (n1, n2) != (u, v):
                weight = G.edges[n1, n2]['weight']
                potential_edges.append((n1, n2, weight))

    if not potential_edges:
        tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return generate_neighbor_tree(G, tree, max_children, penalty)

    # Sort by weight
    potential_edges.sort(key=lambda x: x[2])

    # Pick from the better edges with some randomness
    # More likely to pick better edges, but still some exploration
    idx = min(int(random.expovariate(2) * len(potential_edges)), len(potential_edges) - 1)
    n1, n2, _ = potential_edges[idx]

    # Add the new edge
    tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])

    return tree

#==============================================================================
#                           7. FUNZIONI DI MIGLIORAMENTO
#==============================================================================
def try_random_edge_swap(G, current_tree, max_children, penalty, neighborhood_size=1):
    """
    Implementa una strategia best-improvement per il local search.
    Esplora neighborhood_size scambi casuali e applica solo il migliore se migliora il costo.

    Args:
        G: Original graph
        current_tree: Current spanning tree (modificabile in-place)
        max_children: Maximum allowed number of children
        penalty: Penalty for violations
        neighborhood_size: Numero di scambi candidati da provare

    Returns:
        bool: True if improvement was made
    """
    tree_edges = list(current_tree.edges())
    non_tree_edges = [e for e in G.edges() if e not in tree_edges and (e[1], e[0]) not in tree_edges]

    if not non_tree_edges:
        return False

    best_cost = calculate_cost_local(current_tree, max_children, penalty)
    best_tree = None
    best_swap_info = None

    # Esplora neighborhood_size scambi candidati
    for attempt in range(neighborhood_size):
        edge_to_remove = random.choice(tree_edges)
        edge_to_add = random.choice(non_tree_edges)

        # Crea copia temporanea dell'albero e applica lo scambio
        temp_tree = current_tree.copy()
        temp_tree.remove_edge(*edge_to_remove)
        temp_tree.add_edge(*edge_to_add, weight=G[edge_to_add[0]][edge_to_add[1]]['weight'])

        # Verifica che la nuova struttura sia ancora un albero valido
        if nx.is_connected(temp_tree) and nx.is_tree(temp_tree):
            new_cost = calculate_cost_local(temp_tree, max_children, penalty)

            # Se questo scambio è migliore del migliore trovato finora
            if new_cost < best_cost:
                best_cost = new_cost
                best_tree = temp_tree.copy()
                best_swap_info = (edge_to_remove, edge_to_add, new_cost)

    # Se abbiamo trovato almeno un miglioramento, applica il migliore
    if best_tree is not None:
        current_tree.clear()
        current_tree.add_edges_from(best_tree.edges(data=True))

        # Log opzionale per debug
        if best_swap_info:
            logging.debug(f"Best improvement swap applied: removed {best_swap_info[0]}, "
                         f"added {best_swap_info[1]}, new cost: {best_swap_info[2]}")

        return True

    return False  # nessun miglioramento trovato

def fix_constraint_violations(G, current_tree, constrained_nodes, max_children, penalty, neighborhood_size=1):
    """
    Corregge i vincoli violati provando più alternative per ciascun nodo.
    Utilizza una strategia multi-trial con neighborhood_size tentativi per nodo.

    Args:
        G: Original graph
        current_tree: Current spanning tree (modificabile in-place)
        constrained_nodes: List of nodes violating child constraints
        max_children: Maximum allowed number of children
        penalty: Penalty for violations
        neighborhood_size: Numero di tentativi per ciascun nodo violante

    Returns:
        bool: True if improvement was made
    """
    modified = False
    best_cost = calculate_cost_local(current_tree, max_children, penalty)

    for node in constrained_nodes:
        # Ottieni gli archi del nodo violante e gli archi non presenti nell'albero
        tree_edges_node = [(neighbor, current_tree.edges[node, neighbor]['weight'])
                          for neighbor in current_tree.neighbors(node)]

        # Trova archi potenziali dal grafo originale che non sono nell'albero
        non_tree_edges_node = []
        for neighbor in G.neighbors(node):
            if not current_tree.has_edge(node, neighbor):
                weight = G.edges[node, neighbor]['weight']
                non_tree_edges_node.append((neighbor, weight))

        if not tree_edges_node or not non_tree_edges_node:
            continue  # Salta se non ci sono opzioni di scambio

        best_tree_for_node = None
        best_cost_for_node = best_cost

        # Prova neighborhood_size tentativi per questo nodo
        for attempt in range(neighborhood_size):
            # Seleziona casualmente un arco da rimuovere (preferendo quelli ad alto peso)
            tree_edges_node.sort(key=lambda x: -x[1])  # Ordina per peso decrescente

            # Selezione probabilistica che favorisce archi ad alto peso
            if len(tree_edges_node) > 1:
                # Usa distribuzione esponenziale per favorire archi pesanti
                idx = min(int(random.expovariate(2) * len(tree_edges_node)), len(tree_edges_node) - 1)
                neighbor_to_remove, _ = tree_edges_node[idx]
            else:
                neighbor_to_remove, _ = tree_edges_node[0]

            # Seleziona casualmente un arco da aggiungere (preferendo quelli a basso peso)
            non_tree_edges_node.sort(key=lambda x: x[1])  # Ordina per peso crescente

            if len(non_tree_edges_node) > 1:
                # Usa distribuzione esponenziale per favorire archi leggeri
                idx = min(int(random.expovariate(2) * len(non_tree_edges_node)), len(non_tree_edges_node) - 1)
                neighbor_to_add, _ = non_tree_edges_node[idx]
            else:
                neighbor_to_add, _ = non_tree_edges_node[0]

            # Crea copia temporanea e applica lo scambio
            temp_tree = current_tree.copy()
            temp_tree.remove_edge(node, neighbor_to_remove)
            temp_tree.add_edge(node, neighbor_to_add, weight=G[node][neighbor_to_add]['weight'])

            # Verifica che la nuova struttura sia ancora un albero valido e connesso
            if nx.is_connected(temp_tree) and nx.is_tree(temp_tree):
                new_cost = calculate_cost_local(temp_tree, max_children, penalty)

                # Se questo tentativo è migliore del migliore per questo nodo
                if new_cost < best_cost_for_node:
                    best_cost_for_node = new_cost
                    best_tree_for_node = temp_tree.copy()

        # Se abbiamo trovato un miglioramento per questo nodo, applicalo
        if best_tree_for_node is not None:
            current_tree.clear()
            current_tree.add_edges_from(best_tree_for_node.edges(data=True))
            best_cost = best_cost_for_node
            modified = True

            # Log opzionale per debug
            logging.debug(f"Constraint violation fixed for node {node}, new cost: {best_cost}")

    return modified

def _improve_tree_locally(G, tree, max_children, penalty):
    """
    Performs a quick local improvement on the tree.
    """
    improved = True
    improvement_rounds = 0

    while improved and improvement_rounds < 5:  # Limit to 5 rounds
        improved = False
        improvement_rounds += 1

        # Try to reduce child constraint violations
        constrained_nodes = get_violating_nodes(tree, max_children)
        if constrained_nodes:
            # Try to fix one violation
            node = random.choice(constrained_nodes)
            neighbors = list(tree.neighbors(node))

            # Sort edges by weight (prefer to remove higher weight edges)
            edges_to_remove = [(node, neighbor, tree.edges[node, neighbor]['weight'])
                              for neighbor in neighbors]
            edges_to_remove.sort(key=lambda x: -x[2])  # Sort by weight descending

            for _, neighbor, _ in edges_to_remove:
                # Try removing this edge
                tree.remove_edge(node, neighbor)

                # Check if tree is still connected
                if not nx.is_connected(tree):
                    # Find alternative connection
                    best_alternative = None
                    best_weight = float('inf')

                    components = list(nx.connected_components(tree))
                    comp1 = [c for c in components if node in c][0]
                    comp2 = [c for c in components if neighbor in c][0]

                    for n1 in comp1:
                        for n2 in comp2:
                            if G.has_edge(n1, n2) and (n1, n2) != (node, neighbor):
                                weight = G.edges[n1, n2]['weight']
                                if weight < best_weight:
                                    best_weight = weight
                                    best_alternative = (n1, n2)

                    if best_alternative:
                        n1, n2 = best_alternative
                        tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])
                        improved = True
                        break
                    else:
                        # No alternative found, put back the original edge
                        tree.add_edge(node, neighbor, weight=G.edges[node, neighbor]['weight'])

        # If no constraints violation fixes were made, try edge swaps for cost improvement
        if not improved:
            original_cost = calculate_cost_local(tree, max_children, penalty)

            # Try some random edge swaps
            for _ in range(5):  # Try a limited number of swaps
                edge_to_remove = random.choice(list(tree.edges()))
                u, v = edge_to_remove

                # Remove the edge
                tree.remove_edge(u, v)

                # Check if tree is still connected (should not be)
                components = list(nx.connected_components(tree))
                if len(components) == 1:  # This should not happen in a proper tree
                    continue

                # Find an alternative edge to connect the components
                comp1, comp2 = components[0], components[1]
                best_edge = None
                best_cost = float('inf')

                candidate_edges = []
                for n1 in comp1:
                    for n2 in comp2:
                        if G.has_edge(n1, n2) and (n1, n2) != (u, v):
                            candidate_edges.append((n1, n2))

                if candidate_edges:
                    # Try each candidate edge and evaluate cost
                    for edge in candidate_edges:
                        n1, n2 = edge
                        tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])

                        cost = calculate_cost_local(tree, max_children, penalty)
                        if cost < best_cost:
                            best_cost = cost
                            best_edge = edge

                        # Remove the edge for next iteration
                        tree.remove_edge(n1, n2)

                    # Add the best edge found
                    if best_edge:
                        n1, n2 = best_edge
                        tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])

                        if best_cost < original_cost:
                            improved = True
                        else:
                            # If no improvement found, revert to original tree structure
                            tree.remove_edge(n1, n2)
                            tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
                else:
                    # No candidate edges found, restore original edge
                    tree.add_edge(u, v, weight=G.edges[u, v]['weight'])

    return tree

def _improve_best_solution(G, tree, max_children, penalty):
    """
    Final intensification to improve the best solution found.
    Uses a combination of strategies to try to find better solutions.
    """
    best_tree = tree.copy()
    best_cost = calculate_cost_sa(tree, max_children, penalty)

    # Try a more exhaustive edge swap approach
    for u, v in list(best_tree.edges()):
        # Remove the edge
        best_tree.remove_edge(u, v)

        # Find the components
        components = list(nx.connected_components(best_tree))
        if len(components) != 2:  # This should not happen in a tree
            best_tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
            continue

        comp1, comp2 = components

        # Try all possible alternative edges
        alternatives = []
        for n1 in comp1:
            for n2 in comp2:
                if G.has_edge(n1, n2) and (n1, n2) != (u, v):
                    weight = G.edges[n1, n2]['weight']
                    alternatives.append((n1, n2, weight))

        # Sort by weight ascending
        alternatives.sort(key=lambda x: x[2])

        # Try the top 5 alternatives
        for i, (n1, n2, _) in enumerate(alternatives[:5]):
            best_tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])
            new_cost = calculate_cost_sa(best_tree, max_children, penalty)

            if new_cost < best_cost:
                best_cost = new_cost
                # Keep this improvement and continue
                break
            else:
                # Undo this change
                best_tree.remove_edge(n1, n2)
                # If this was the last alternative, put back the original edge
                if i == min(4, len(alternatives) - 1):
                    best_tree.add_edge(u, v, weight=G.edges[u, v]['weight'])

    # Try to fix child constraint violations more aggressively
    violating_nodes = get_violating_nodes(best_tree, max_children)
    constrained_nodes = []
    for node in violating_nodes:
        children_count = len([child for child in best_tree.neighbors(node)
                             if best_tree.degree(child) < best_tree.degree(node)])
        constrained_nodes.append((node, children_count))

    if constrained_nodes:
        # Sort by violation severity
        constrained_nodes.sort(key=lambda x: x[1], reverse=True)

        # Try to fix the worst violations
        for node, _ in constrained_nodes[:3]:  # Focus on worst 3 violations
            neighbors = list(best_tree.neighbors(node))

            # Try removing each edge and finding the best alternative
            for neighbor in neighbors:
                best_tree.remove_edge(node, neighbor)

                if not nx.is_connected(best_tree):
                    # Find components
                    components = list(nx.connected_components(best_tree))
                    comp1 = [c for c in components if node in c][0]
                    comp2 = [c for c in components if neighbor in c][0]

                    # Find alternative connections that don't involve the constrained node
                    alt_edges = []
                    for n1 in comp1:
                        if n1 == node:
                            continue  # Skip the constrained node
                        for n2 in comp2:
                            if G.has_edge(n1, n2):
                                weight = G.edges[n1, n2]['weight']
                                alt_edges.append((n1, n2, weight))

                    if alt_edges:
                        # Sort by weight
                        alt_edges.sort(key=lambda x: x[2])

                        # Pick one of the best alternatives with some randomness
                        idx = min(int(random.expovariate(1) * len(alt_edges)), len(alt_edges) - 1)
                        n1, n2, _ = alt_edges[idx]
                        best_tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])
                        return best_tree  # Successfully modified
                    else:
                        # No alternative found, put back the original edge
                        best_tree.add_edge(node, neighbor, weight=G.edges[node, neighbor]['weight'])

    # If we get here, either there are no constraint violations or we couldn't fix them
    # Try a standard edge swap but with more focus on high-cost edges

    # Find high-cost edges in the tree
    edges = [(u, v, best_tree.edges[u, v]['weight']) for u, v in best_tree.edges()]
    edges.sort(key=lambda x: -x[2])  # Sort by weight, highest first

    # Try to replace one of the highest-cost edges
    edge_idx = min(int(random.expovariate(0.5) * len(edges)), len(edges) - 1)
    u, v, _ = edges[edge_idx]

    # Remove this edge
    best_tree.remove_edge(u, v)

    # Standard reconnection logic similar to generate_neighbor_tree
    components = list(nx.connected_components(best_tree))

    if len(components) == 1:
        # The edge didn't disconnect the tree (shouldn't happen in a proper tree)
        best_tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return generate_neighbor_tree(G, best_tree, max_children, penalty)

    # Find a new edge to connect components
    comp1, comp2 = components[0], components[1]

    potential_edges = []
    for n1 in comp1:
        for n2 in comp2:
            if G.has_edge(n1, n2) and (n1, n2) != (u, v):
                weight = G.edges[n1, n2]['weight']
                potential_edges.append((n1, n2, weight))

    if not potential_edges:
        best_tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return generate_neighbor_tree(G, best_tree, max_children, penalty)

    # Sort by weight
    potential_edges.sort(key=lambda x: x[2])

    # Pick from the better edges with some randomness
    # More likely to pick better edges, but still some exploration
    idx = min(int(random.expovariate(2) * len(potential_edges)), len(potential_edges) - 1)
    n1, n2, _ = potential_edges[idx]

    # Add the new edge
    best_tree.add_edge(n1, n2, weight=G.edges[n1, n2]['weight'])

    return best_tree

#==============================================================================
#                           8. BENCMARKING E TEST
#==============================================================================
def test_instance(G, max_children, penalty, instance_name="", stop_event=None, queue=None, progress_info=None):
    """
    Test different spanning tree algorithms on a graph instance.

    Args:
        G (nx.Graph): The input graph.
        max_children (int): Maximum allowed number of children for each node.
        penalty (int): Penalty value for child constraint violations.
        instance_name (str): Name of the instance for reporting.
        stop_event (threading.Event): Event to signal stopping.
        queue (queue.Queue): Queue for progress updates.
        progress_info (dict): Dictionary with progress tracking information:
                             - start_progress: Starting point for progress percentage
                             - total_progress: Total progress percentage allocated for this instance

    Returns:
        dict: Metrics for each algorithm.
    """
    # Optimize memory representation for large graphs
    if len(G.nodes()) > 100:  # Solo per grafi di dimensioni significative
        if queue:
            queue.put(("log", (f"Ottimizzando rappresentazione del grafo per {instance_name}...", "info")))
        G_opt, node_mapping, adj_matrix = optimize_memory_usage(G.copy())
        G = G_opt  # Usa il grafo ottimizzato
        results = {"graph": G, "node_mapping": node_mapping}
    else:
        G = G.copy()
        results = {"graph": G}

    # Set default progress tracking if not provided
    if progress_info is None:
        progress_info = {
            "start_progress": 0,
            "total_progress": 100,
            "queue": queue
        }

    # Helper function to update progress with proper scaling
    def update_progress(phase, phase_progress, algorithm=""):
        if queue:
            # Scale the progress relative to the overall calculation
            # Each algorithm gets roughly 1/3 of the total instance progress
            start = progress_info["start_progress"]
            total = progress_info["total_progress"]

            # Algorithms get different portions of the total progress
            algorithm_portions = {
                "greedy": 0.2,  # 20% for greedy
                "local": 0.3,   # 30% for local search
                "sa": 0.5       # 50% for simulated annealing
            }

            # Calculate which portion of progress we're in
            if algorithm == "greedy":
                algo_start = start
                algo_total = total * algorithm_portions["greedy"]
            elif algorithm == "local":
                algo_start = start + total * algorithm_portions["greedy"]
                algo_total = total * algorithm_portions["local"]
            elif algorithm == "sa":
                algo_start = start + total * (algorithm_portions["greedy"] + algorithm_portions["local"])
                algo_total = total * algorithm_portions["sa"]
            else:
                # For general updates not tied to a specific algorithm
                algo_start = start
                algo_total = total

            # Calculate the scaled progress
            scaled_progress = algo_start + (phase_progress / 100.0) * algo_total

            # Update the UI
            queue.put(("phase", f"{phase}"))
            queue.put(("progress", int(scaled_progress)))
            if algorithm:
                queue.put(("algorithm", algorithm))

    # Function to check if stop is requested
    def check_stop():
        if stop_event and stop_event.is_set():
            return True
        return False

    # Track memory usage
    def get_memory_usage():
        gc.collect()  # Force garbage collection
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / 1024  # in KB

    # 1. Run Greedy Algorithm
    if check_stop():
        return results

    update_progress("Greedy Spanning Tree", 0, "greedy")
    if queue:
        queue.put(("log", (f"Esecuzione algoritmo greedy per {instance_name}...", "info")))

    start_memory = get_memory_usage()
    start_time = time.time()

    greedy_tree, greedy_cost = greedy_spanning_tree(G, max_children, penalty)
    end_time = time.time()
    end_memory = get_memory_usage()

    greedy_time = end_time - start_time
    greedy_memory = max(0, end_memory - start_memory)  # Ensure non-negative memory usage

    # Fix memoria = 0.0 bug
    if greedy_memory == 0.0:
        greedy_memory = psutil.Process().memory_info().rss / 1024  # fallback in KB

    # Calcola violazioni dei vincoli
    greedy_violations = count_constraint_violations(greedy_tree, max_children)

    # Test di coerenza (solo in debug mode)
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        if not test_violations_consistency(greedy_tree, max_children):
            logging.warning("Inconsistenza rilevata nel calcolo delle violazioni per Greedy")

    results["greedy_tree"] = greedy_tree
    results["greedy_cost"] = greedy_cost
    results["greedy_time"] = greedy_time
    results["greedy_memory"] = greedy_memory
    results["greedy_violations"] = greedy_violations
    results["greedy_calls"] = greedy_cost_calls[0]  # Store actual call count

    if queue:
        queue.put(("log", (f"Greedy completato: costo={greedy_cost}, tempo={greedy_time:.4f}s, chiamate={greedy_cost_calls[0]}, violazioni={greedy_violations}", "success")))

    update_progress("Greedy Spanning Tree", 100, "greedy")

    # 2. Run Local Search
    if check_stop():
        return results

    update_progress("Local Search", 0, "local")
    if queue:
        queue.put(("log", (f"Esecuzione ricerca locale per {instance_name}...", "info")))

    start_memory = get_memory_usage()
    start_time = time.time()

    # Use parallel version for graphs larger than a threshold
    if len(G.nodes()) > 50:
        num_threads = min(8, os.cpu_count() or 4)  # Limita a 8 thread o meno
        local_tree, local_search_cost_calls[0], local_score_history = parallel_local_search(G, greedy_tree, max_children, penalty, num_threads=num_threads)
        if queue:
            queue.put(("log", (f"Utilizzati {num_threads} thread per la ricerca locale", "info")))
    else:
        local_tree, local_search_cost_calls[0], local_score_history = adaptive_neighborhood_local_search(G, greedy_tree, max_children, penalty)

    end_time = time.time()
    end_memory = get_memory_usage()

    local_cost = calculate_cost_local(local_tree, max_children, penalty)
    local_time = end_time - start_time
    local_memory = max(0, end_memory - start_memory)  # Ensure non-negative memory usage

    # Fix memoria = 0.0 bug
    if local_memory == 0.0:
        local_memory = psutil.Process().memory_info().rss / 1024  # fallback in KB

    # Calcola violazioni dei vincoli
    local_violations = count_constraint_violations(local_tree, max_children)

    results["local_tree"] = local_tree
    results["local_cost"] = local_cost
    results["local_time"] = local_time
    results["local_memory"] = local_memory
    results["local_violations"] = local_violations
    results["local_calls"] = local_search_cost_calls[0]  # Usa il valore restituito dalla funzione
    results["local_score_history"] = local_score_history

    if queue:
        queue.put(("log", (f"Ricerca locale completata: costo={local_cost}, tempo={local_time:.4f}s, chiamate={local_search_cost_calls[0]}, violazioni={local_violations}", "success")))

    update_progress("Local Search", 100, "local")

    # 3. Run Simulated Annealing
    if check_stop():
        return results

    update_progress("Simulated Annealing", 0, "sa")
    if queue:
        queue.put(("log", (f"Esecuzione simulated annealing per {instance_name}...", "info")))
        queue.put(("log", (f"Utilizzo dell'albero ottimizzato da Local Search come soluzione iniziale", "info")))

    start_memory = get_memory_usage()
    start_time = time.time()

    # Create a callback for SA that updates progress
    def sa_progress_callback(iteration, temperature, current_cost, accepted, total_iterations):
        if queue and iteration % max(1, total_iterations // 50) == 0:  # Update more frequently
            progress_pct = min(100, (iteration / total_iterations) * 100)
            update_progress("Simulated Annealing", progress_pct, "sa")

            # Send detailed parameters to the UI
            queue.put(("temp", f"{temperature:.6f}"))
            queue.put(("iter", f"{iteration}/{total_iterations}"))
            queue.put(("cost", f"{current_cost}"))
            queue.put(("accept", f"{accepted}"))

            # Log detailed progress at regular intervals
            if iteration % max(1, total_iterations // 10) == 0:  # Log every 10%
                queue.put(("log", (f"SA: It. {iteration}/{total_iterations}, Temp: {temperature:.6f}, Costo: {current_cost}", "info")))

    # Utilizza local_tree invece di greedy_tree come soluzione iniziale per SA
    sa_tree, sa_cost, sa_iterations, sa_accepts, sa_score_history = simulated_annealing_spanning_tree(
        G, max_children, penalty,
        initial_tree=local_tree,  # Usa l'albero ottimizzato dalla ricerca locale
        stop_event=stop_event,
        queue=queue,
        progress_callback=sa_progress_callback
    )

    end_time = time.time()
    end_memory = get_memory_usage()

    sa_cost = calculate_cost_sa(sa_tree, max_children, penalty)
    sa_time = end_time - start_time
    sa_memory = max(0, end_memory - start_memory)  # Ensure non-negative memory usage

    # Fix memoria = 0.0 bug
    if sa_memory == 0.0:
        sa_memory = psutil.Process().memory_info().rss / 1024  # fallback in KB

    # Calcola violazioni dei vincoli
    sa_violations = count_constraint_violations(sa_tree, max_children)

    results["sa_tree"] = sa_tree
    results["sa_cost"] = sa_cost
    results["sa_time"] = sa_time
    results["sa_memory"] = sa_memory
    results["sa_violations"] = sa_violations
    results["sa_calls"] = sa_cost_calls[0]
    results["sa_iterations"] = sa_iterations  # Keep track of actual iterations
    results["sa_score_history"] = sa_score_history

    if queue:
        acceptance_rate = (sa_accepts / sa_iterations * 100) if sa_iterations > 0 else 0
        queue.put(("log", (f"SA completato: costo={sa_cost}, tempo={sa_time:.4f}s, " +
                          f"iterazioni={sa_iterations}, chiamate={sa_cost_calls[0]}, accettazioni={sa_accepts} " +
                          f"({acceptance_rate:.2f}%), violazioni={sa_violations}", "success")))

    update_progress("Simulated Annealing", 100, "sa")

    return results

#==============================================================================
#                           9. OTTIMIZZAZIONE E PARALLELISMO
#==============================================================================
def optimize_memory_usage(G):
    """
    Optimize graph memory usage by using more efficient data structures.

    Args:
        G (nx.Graph): The input graph.

    Returns:
        Tuple: Optimized graph, node mapping, and adjacency matrix.
    """
    # Relabel nodes to use integers for more efficient memory usage
    mapping = {node: idx for idx, node in enumerate(G.nodes())}
    G = nx.relabel_nodes(G, mapping)

    # Convert to a sparse adjacency matrix
    try:
        # For newer NetworkX versions (2.8+)
        adjacency_matrix = nx.to_scipy_sparse_array(G, format='csr')
    except AttributeError:
        # For older NetworkX versions
        adjacency_matrix = nx.to_scipy_sparse_matrix(G, format='csr')

    return G, mapping, adjacency_matrix

def parallel_local_search(G, initial_tree, max_degree, penalty, num_threads=4, stop_event=None, queue=None):
    """
    Parallel version of the local search algorithm.
    """
    def local_search_task():
        return adaptive_neighborhood_local_search(G, initial_tree.copy(), max_degree, penalty, stop_event=stop_event, queue=queue)

    # Crea una copia del grafo iniziale per ogni thread
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(local_search_task) for _ in range(num_threads)]

        # Raccoglie i risultati man mano che i thread terminano
        total_calls = 0
        best_score_history = []
        for future in concurrent.futures.as_completed(futures):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False)
                break

            tree, calls, score_history = future.result()
            results.append((tree, calls, score_history))
            total_calls += calls
            if len(score_history) > len(best_score_history):
                best_score_history = score_history

    # Trova il miglior risultato tra tutti i thread
    if results:
        best_result = min(results, key=lambda x: calculate_cost_local(x[0], max_degree, penalty))
        return best_result[0], total_calls, best_result[2]  # Restituisce anche lo score_history
    else:
        # Fallback in caso di interruzione
        return initial_tree.copy(), 0, []

#==============================================================================
#                           9. VALUTAZIONE E PUNTEGGIO
#==============================================================================
def evaluate_solution(solution, reference_values):
    """
    Restituisce un punteggio normalizzato su 100 (più alto = migliore).
    Pesa nell'ordine: costo, violazioni, tempo, memoria.

    Args:
        solution (dict): Dizionario con chiavi 'cost', 'violations', 'execution_time', 'memory'
        reference_values (dict): Valori di riferimento per normalizzazione con chiavi
                                'max_cost', 'max_violations', 'max_time', 'max_memory'

    Returns:
        float: Punteggio normalizzato su 100 (più alto = migliore)
    """
    score = 100.0

    def penalize(value, max_val, weight):
        """Calcola la penalità normalizzata per una metrica."""
        if max_val == 0 or value == 0:
            return 0
        return weight * (value / max_val)

    # Normalizza rispetto al massimo osservato per ciascuna metrica
    # Pesi: costo (40%), violazioni (30%), tempo (20%), memoria (10%)
    cost_penalty = penalize(solution["cost"], reference_values["max_cost"], 40.0)
    viol_penalty = penalize(solution["violations"], reference_values["max_violations"], 30.0)
    time_penalty = penalize(solution["execution_time"], reference_values["max_time"], 20.0)
    memory_penalty = penalize(solution["memory"], reference_values["max_memory"], 10.0)

    # Sottrai le penalità dal punteggio base
    score -= (cost_penalty + viol_penalty + time_penalty + memory_penalty)

    # Assicurati che il punteggio sia sempre positivo
    score = max(score, 0.0)

    return round(score, 2)

def count_constraint_violations(tree, max_children):
    """
    Conta il numero di nodi che violano i vincoli di grado.
    Questa è la funzione centralizzata per il calcolo delle violazioni.

    Args:
        tree: Spanning tree
        max_children: Numero massimo di figli consentiti

    Returns:
        int: Numero di nodi che violano i vincoli
    """
    violations = 0
    for node in tree.nodes():
        children = [child for child in tree.neighbors(node)
                   if tree.degree(child) < tree.degree(node)]
        if len(children) > max_children:
            violations += 1
    return violations

def get_violating_nodes(tree, max_children):
    """
    Restituisce la lista dei nodi che violano i vincoli di grado.
    Funzione di supporto per evitare duplicazione di codice.

    Args:
        tree: Spanning tree
        max_children: Numero massimo di figli consentiti

    Returns:
        list: Lista di nodi che violano i vincoli
    """
    violating_nodes = []
    for node in tree.nodes():
        children = [child for child in tree.neighbors(node)
                   if tree.degree(child) < tree.degree(node)]
        if len(children) > max_children:
            violating_nodes.append(node)
    return violating_nodes

def test_violations_consistency(tree, max_children):
    """
    Funzione di test per verificare la coerenza del calcolo delle violazioni.
    Confronta il risultato della funzione centralizzata con un calcolo diretto.

    Args:
        tree: Spanning tree da testare
        max_children: Numero massimo di figli consentiti

    Returns:
        bool: True se i calcoli sono coerenti, False altrimenti
    """
    # Calcolo con funzione centralizzata
    violations_centralized = count_constraint_violations(tree, max_children)
    violating_nodes_centralized = get_violating_nodes(tree, max_children)

    # Calcolo diretto per verifica
    violations_direct = 0
    violating_nodes_direct = []

    for node in tree.nodes():
        children = [child for child in tree.neighbors(node)
                   if tree.degree(child) < tree.degree(node)]
        if len(children) > max_children:
            violations_direct += 1
            violating_nodes_direct.append(node)

    # Verifica coerenza
    count_consistent = violations_centralized == violations_direct
    nodes_consistent = set(violating_nodes_centralized) == set(violating_nodes_direct)

    if not count_consistent or not nodes_consistent:
        logging.error(f"INCONSISTENZA RILEVATA nel calcolo delle violazioni!")
        logging.error(f"Violazioni centralizzate: {violations_centralized}")
        logging.error(f"Violazioni dirette: {violations_direct}")
        logging.error(f"Nodi violanti centralizzati: {violating_nodes_centralized}")
        logging.error(f"Nodi violanti diretti: {violating_nodes_direct}")
        return False

    return True
# app/_init_.py

"""
Inizializzazione del pacchetto App.

Questo modulo inizializza l'applicazione DCST (Degree-Constrained Spanning Tree) Tool.
Fornisce un'interfaccia pulita per l'importazione delle varie componenti dell'applicazione.
"""

# Versione dell'applicazione
__version__ = '1.0.0'
__author__ = 'DCST Tool Team'

# Importazione delle funzionalità principali
try:
    from .algorithms import (
        test_instance,
        calculate_cost_base, 
        greedy_spanning_tree,
        adaptive_neighborhood_local_search,
        simulated_annealing_spanning_tree
    )
except ImportError as e:
    print(f"Errore importazione algoritmi: {e}")

# Importazione di utilitá per la generazione di grafi e la visualizzazione
from .utils import (
    generate_connected_random_graph,
    draw_and_save_graph,
    save_table_as_image
)

# Componenti della GUI
from .gui import App, QueueHandler

# Configurazione del logging
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Esportazione delle funzionalità principali
__all__ = [
    'App', 
    'test_instance',
    'generate_connected_random_graph',
    'draw_and_save_graph',
    'save_table_as_image',
    'calculate_cost',
    'greedy_spanning_tree',
    'adaptive_neighborhood_local_search',
    'simulated_annealing_spanning_tree'
]



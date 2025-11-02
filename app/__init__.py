"""
DCST Tool package initialization (minimal).
Exposes the minimal GUI App and selected core functions without heavy side effects.
"""

import logging

__version__ = '1.0.0'
__author__ = 'DCST Tool Team'

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Optional GUI export
try:
    from .gui import App  # noqa: F401
except Exception:
    App = None  # type: ignore

# Core algorithms and utilities that are safe to import
try:
    from .algorithms import (
        run_instance,
        calculate_cost_base,
        greedy_spanning_tree,
        adaptive_neighborhood_local_search,
        simulated_annealing_spanning_tree,
    )  # noqa: F401
except Exception:
    # Keep package importable even if heavy deps are missing
    run_instance = None  # type: ignore
    calculate_cost_base = None  # type: ignore
    greedy_spanning_tree = None  # type: ignore
    adaptive_neighborhood_local_search = None  # type: ignore
    simulated_annealing_spanning_tree = None  # type: ignore

try:
    from .utils_core import (
        generate_connected_random_graph,
        draw_and_save_graph,
        save_table_as_image,
    )  # noqa: F401
except Exception:
    generate_connected_random_graph = None  # type: ignore
    draw_and_save_graph = None  # type: ignore
    save_table_as_image = None  # type: ignore

__all__ = [
    'App',
    'run_instance',
    'generate_connected_random_graph',
    'draw_and_save_graph',
    'save_table_as_image',
    'calculate_cost_base',
    'greedy_spanning_tree',
    'adaptive_neighborhood_local_search',
    'simulated_annealing_spanning_tree',
]



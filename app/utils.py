"""
Minimal utilities used by the simplified GUI (core).
Exposed functions:
 - generate_connected_random_graph
 - draw_and_save_graph
 - save_table_as_image
 - plot_score_evolution
 - get_current_plot_directory
 - reset_plot_directory
"""

from __future__ import annotations

import os
import random
import logging
from typing import Dict, Any
import shutil

import matplotlib
matplotlib.use('Agg')  # non-interactive backend for headless save
import matplotlib.pyplot as plt
from matplotlib.table import Table
import networkx as nx

from .config import (
    DESKTOP_FALLBACK_NAMES,
    DEFAULT_PLOT_DIR_NAME,
    FALLBACK_PLOT_PREFIX,
    MAX_PLOT_DIRECTORIES,
    NODE_COLORS,
    ALGORITHM_COLORS,
    GRAPH_FIGURE_SIZE,
    TABLE_FIGURE_SIZE,
    IMAGE_DPI,
    TABLE_IMAGE_DPI,
)

_current_plot_dir: str | None = None

# -----------------------------
# Plot directory helpers
# -----------------------------

def _desktop_path() -> str:
    """Best-effort Desktop path or a sensible fallback."""
    candidates = []
    if os.name == 'nt':
        up = os.environ.get('USERPROFILE') or os.path.expanduser('~')
        candidates.append(os.path.join(up, 'Desktop'))
    else:
        candidates.append(os.path.join(os.path.expanduser('~'), 'Desktop'))
    home = os.path.expanduser('~')
    for name in DESKTOP_FALLBACK_NAMES:
        candidates.append(os.path.join(home, name))
    candidates.append(os.getcwd())
    for c in candidates:
        if os.path.isdir(c):
            return c
    return os.getcwd()


def reset_plot_directory() -> str:
    """Create a fresh Plot directory for this session and remember it."""
    global _current_plot_dir
    base = _desktop_path()
    # First try DEFAULT_PLOT_DIR_NAME (unique suffix if taken)
    for i in range(MAX_PLOT_DIRECTORIES):
        name = DEFAULT_PLOT_DIR_NAME if i == 0 else f"{DEFAULT_PLOT_DIR_NAME}_{i:03d}"
        path = os.path.join(base, name)
        try:
            os.makedirs(path, exist_ok=False)
            _current_plot_dir = path
            return path
        except FileExistsError:
            continue
        except Exception:
            break
    # Fallback prefix
    for i in range(MAX_PLOT_DIRECTORIES):
        name = f"{FALLBACK_PLOT_PREFIX}_{i:03d}"
        path = os.path.join(base, name)
        try:
            os.makedirs(path, exist_ok=False)
            _current_plot_dir = path
            return path
        except FileExistsError:
            continue
        except Exception:
            pass
    # Last resort
    _current_plot_dir = os.path.join(os.getcwd(), DEFAULT_PLOT_DIR_NAME)
    os.makedirs(_current_plot_dir, exist_ok=True)
    return _current_plot_dir


def get_current_plot_directory() -> str:
    """Return the current plot directory, creating one if missing."""
    global _current_plot_dir
    if not _current_plot_dir or not os.path.isdir(_current_plot_dir):
        return reset_plot_directory()
    return _current_plot_dir


def delete_current_plot_directory() -> bool:
    """Delete the current plot directory (if any) and reset pointer.

    Returns True if deletion was attempted successfully (directory removed or did not exist),
    False if an unexpected error occurred.
    """
    global _current_plot_dir
    try:
        path = _current_plot_dir
        _current_plot_dir = None
        if path and os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        return True
    except Exception:
        return False


# -----------------------------
# Graph generation and drawing
# -----------------------------

def generate_connected_random_graph(n: int, p: float = 0.3) -> nx.Graph:
    """Generate a simple connected random graph with weights in [1,10]."""
    if n < 2:
        G = nx.Graph()
        G.add_node(0)
        return G
    attempts = 0
    while attempts < 100:
        G = nx.gnp_random_graph(n, p)
        if nx.is_connected(G):
            break
        attempts += 1
        p = min(0.99, p + 0.05)
    if not nx.is_connected(G):
        components = [list(c) for c in nx.connected_components(G)]
        for i in range(len(components)-1):
            u = random.choice(components[i])
            v = random.choice(components[i+1])
            G.add_edge(u, v)
    for u, v in G.edges():
        G[u][v]['weight'] = random.randint(1, 10)
    return G


def draw_and_save_graph(G: nx.Graph, filename: str, max_children: int | None = None, is_spanning_tree: bool = False) -> bool:
    """Draw a graph and save it to the current plot directory."""
    if len(G.nodes()) == 0:
        return False
    plot_dir = get_current_plot_directory()
    full_path = filename if os.path.isabs(filename) else os.path.join(plot_dir, filename)

    pos = nx.kamada_kawai_layout(G) if is_spanning_tree else nx.spring_layout(G, seed=42)
    if is_spanning_tree:
        violating = []
        if max_children is not None:
            try:
                violating = [n for n, d in G.degree() if d > int(max_children)]
            except Exception:
                violating = []
        colors = []
        for node in G.nodes():
            if node == 0:
                colors.append(NODE_COLORS.get("root", "#32CD32"))
            elif node in violating:
                colors.append(NODE_COLORS.get("violating", "#FF0000"))
            else:
                colors.append(NODE_COLORS.get("normal", "#3776ab"))
    else:
        colors = [NODE_COLORS.get("default", "#3776ab") for _ in G.nodes()]

    plt.figure(figsize=GRAPH_FIGURE_SIZE)
    nx.draw(G, pos, with_labels=True, node_color=colors, node_size=800, font_size=10, edge_color='gray', width=2)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    try:
        plt.savefig(full_path, bbox_inches='tight', dpi=IMAGE_DPI)
        plt.close()
        return True
    except Exception as e:
        logging.error(f"Error saving graph: {e}")
        try:
            plt.close()
        except Exception:
            pass
        return False


# -----------------------------
# Table and score plotting
# -----------------------------

def save_table_as_image(table_data, filename: str) -> bool:
    """Save a simple colored comparison table image.
    Expects a pandas DataFrame or DataFrame-like. If pandas is unavailable,
    only minimal validation is performed.
    """
    try:
        import pandas as pd  # optional
    except Exception:
        pd = None

    # Normalize to DataFrame if possible
    if pd is not None and not isinstance(table_data, pd.DataFrame):
        try:
            table_data = pd.DataFrame(table_data)
        except Exception:
            pass

    # Basic validation
    try:
        rows = len(table_data)
        cols = list(table_data.columns)
    except Exception:
        logging.error("Invalid table data; expected pandas DataFrame or similar")
        return False
    if rows < 1:
        return False

    fig, ax = plt.subplots(figsize=TABLE_FIGURE_SIZE)
    ax.set_axis_off()
    fig.patch.set_facecolor('white')

    table = Table(ax, bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    # Header
    for j, col in enumerate(cols):
        cell = table.add_cell(0, j, 1, 1, text=str(col), loc='center', edgecolor='black', facecolor='#E5E8E8')
        cell.set_text_props(color='black', fontweight='bold', fontsize=10)

    algo_col = None
    for c in ("Algoritmo", "Algorithm", "algorithm"):
        if c in cols:
            algo_col = c
            break

    for i, (_, row) in enumerate(getattr(table_data, 'iterrows', lambda: [])(), start=1):
        algo = str(row.get(algo_col, "")) if algo_col else ""
        base_color = ALGORITHM_COLORS.get(algo, "#FFFFFF")
        for j, col in enumerate(cols):
            val = row.get(col)
            cell_text = "" if val is None else str(val)
            cell = table.add_cell(i, j, 1, 1, text=cell_text, loc='center', edgecolor='black', facecolor=base_color)
            cell.set_text_props(color='black', fontsize=9)

    ax.add_table(table)
    full_path = filename if os.path.isabs(filename) else os.path.join(get_current_plot_directory(), filename)
    try:
        plt.savefig(full_path, bbox_inches='tight', dpi=TABLE_IMAGE_DPI, facecolor='white')
        plt.close(fig)
        return True
    except Exception as e:
        logging.error(f"Error saving table image: {e}")
        try:
            plt.close(fig)
        except Exception:
            pass
        return False


def plot_score_evolution(score_histories: Dict[str, Any], reference_final_values: Dict[str, Any] | None = None, filename: str = "score_evolution.png") -> bool:
    """Plot simple score evolution series for each algorithm label."""
    colors = {
        "SA": "#E74C3C",
        "Local": "#3498DB",
        "Greedy": "#2ECC71",
    }
    fig, ax = plt.subplots(figsize=(12, 7))
    x_max = 0
    for _, hist in score_histories.items():
        if not hist:
            continue
        # Support either a list of (iter, data) tuples or a list of numeric values
        if isinstance(hist, (list, tuple)) and hist and isinstance(hist[0], tuple):
            try:
                x_max = max(x_max, max(it for it, _ in hist if isinstance(it, (int, float))))
            except Exception:
                pass
        else:
            # treat as numeric sequence (e.g., costs or scores)
            try:
                x_max = max(x_max, len(hist))
            except Exception:
                pass
    any_series = False
    for label, hist in score_histories.items():
        if not hist:
            continue
        iters, scores = [], []
        # Case 1: list of (iter, data)
        if isinstance(hist, (list, tuple)) and hist and isinstance(hist[0], tuple):
            for item in hist:
                if isinstance(item, tuple) and len(item) == 2:
                    it, data = item
                    iters.append(it)
                    if isinstance(data, dict):
                        try:
                            from .algorithms import evaluate_solution
                            s = float(evaluate_solution(data, reference_final_values or {}))
                        except Exception:
                            s = float(data.get("score", 0.0))
                    else:
                        try:
                            s = float(data)
                        except Exception:
                            s = 0.0
                    scores.append(s)
        else:
            # Case 2: list of numeric values (e.g., costs); convert using evaluate_solution with refs
            try:
                raw = [float(x) for x in hist]
            except Exception:
                raw = []
            if raw:
                iters = list(range(1, len(raw) + 1))
                scores = []
                for c in raw:
                    try:
                        from .algorithms import evaluate_solution
                        sol = {"cost": c, "execution_time": 0.0, "memory": None, "violations": 0}
                        s = float(evaluate_solution(sol, reference_final_values or {}))
                    except Exception:
                        s = float(c)
                    scores.append(s)
        if iters and scores:
            any_series = True
            col = colors.get(label, "#333333")
            if len(iters) == 1:
                # Draw a labeled single point for single-iteration series (e.g., Greedy)
                ax.plot(iters, scores, label=label, color=col, marker='o', linestyle='None', markersize=8, zorder=5)
            else:
                # Draw line with markers to make short series (e.g., Local) clearly visible
                ax.plot(iters, scores, label=label, color=col, linewidth=2.0, marker='o', markersize=3)
    ax.set_xlabel("Iterazione", fontsize=11)
    ax.set_ylabel("Score (0-100, più alto è meglio)", fontsize=11)
    ax.grid(True, alpha=0.2)
    if any_series:
        ax.legend(loc="best", fontsize=10)
    fig.suptitle("Evoluzione dello Score per Algoritmo", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0.04, 1, 0.98])
    # Ensure x-axis covers the full range including single-point series at x=1
    try:
        ax.set_xlim(0, max(1, int(x_max)))
    except Exception:
        pass
    full_path = filename if os.path.isabs(filename) else os.path.join(get_current_plot_directory(), filename)
    try:
        plt.savefig(full_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close()
        return True
    except Exception as e:
        logging.error(f"Error saving score evolution: {e}")
        try:
            plt.close()
        except Exception:
            pass
        return False

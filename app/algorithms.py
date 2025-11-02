# Simplified algorithms module for DCST Tool
# - Focus on clarity and minimalism for academic purposes
# - Implements: Greedy, Local Search, Simulated Annealing
# - Orchestrator: test_instance (and run_instance alias)
# - No advanced resource mgmt, no parallelization, no dynamic thresholds

import time
import random
import tracemalloc
from typing import Dict, Any, Tuple, List, Optional
from math import log, exp
import networkx as nx

# -------------------------------
# Helpers
# -------------------------------

def _tree_cost(tree: nx.Graph, max_children: int, penalty: int) -> float:
    # Sum of weights + penalty per excess degree
    total = 0.0
    for u, v, data in tree.edges(data=True):
        total += float(data.get("weight", 1))
    # penalty on degree excess
    deg = dict(tree.degree())
    excess = sum(max(0, deg.get(n, 0) - max_children) for n in tree.nodes())
    return total + penalty * excess

def _ensure_weights(G: nx.Graph, default: float = 1.0) -> None:
    for u, v in G.edges():
        if "weight" not in G[u][v]:
            G[u][v]["weight"] = default

def _build_tree_from_edges(nodes: List, edges: List[Tuple[int, int]], G: nx.Graph) -> nx.Graph:
    T = nx.Graph()
    T.add_nodes_from(nodes)
    for u, v in edges:
        w = G[u][v].get("weight", 1)
        T.add_edge(u, v, weight=w)
    return T

# -------------------------------
# Union-Find (single, deduplicated)
# -------------------------------

class UnionFind:
    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
        self.rank = {n: 0 for n in nodes}
        self.components = len(self.parent)

    def find(self, a):
        if self.parent[a] != a:
            self.parent[a] = self.find(self.parent[a])
        return self.parent[a]

    def union(self, a, b) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1
        self.components -= 1
        return True

# -------------------------------
# Algorithms
# -------------------------------

def greedy_spanning_tree(G: nx.Graph, max_children: int = 3, penalty: int = 1000) -> Tuple[nx.Graph, float]:
    """
    Simple Kruskal MST (ignores degree during construction), degree penalty in cost.
    Always returns a spanning tree if G is connected.
    """
    _ensure_weights(G)
    nodes = list(G.nodes())
    edges_sorted = sorted(((G[u][v].get("weight", 1.0), u, v) for u, v in G.edges()), key=lambda x: x[0])

    uf = UnionFind(nodes)
    chosen = []
    for w, u, v in edges_sorted:
        if uf.union(u, v):
            chosen.append((u, v))
        if len(chosen) == len(nodes) - 1:
            break

    T = _build_tree_from_edges(nodes, chosen, G)
    return T, _tree_cost(T, max_children, penalty)

def _neighbor_by_edge_swap(G: nx.Graph, T: nx.Graph) -> Optional[nx.Graph]:
    """Create neighbor tree by adding a random non-tree edge and removing max-weight edge on the induced cycle."""
    non_tree_edges = [(u, v) for u, v in G.edges() if not T.has_edge(u, v)]
    if not non_tree_edges:
        return None
    u, v = random.choice(non_tree_edges)
    # path exists in a tree
    try:
        path = nx.shortest_path(T, source=u, target=v)
    except nx.NetworkXNoPath:
        return None
    # cycle edges = path edges + (u,v)
    cycle_edges = list(zip(path, path[1:])) + [(u, v)]
    # remove the heaviest edge on the path portion (not the new edge)
    path_edges = list(zip(path, path[1:]))
    if not path_edges:
        return None
    heaviest = max(path_edges, key=lambda e: T[e[0]][e[1]].get("weight", 1))
    # build new tree
    T2 = T.copy()
    T2.remove_edge(*heaviest)
    T2.add_edge(u, v, weight=G[u][v].get("weight", 1))
    return T2

def adaptive_neighborhood_local_search(G: nx.Graph, initial_tree: nx.Graph, max_children: int, penalty: int,
                                       max_iterations: int = 500) -> Tuple[nx.Graph, List[float]]:
    """First-improvement local search via edge-swap neighbors."""
    best = initial_tree.copy()
    best_cost = _tree_cost(best, max_children, penalty)
    history = [best_cost]

    for _ in range(max_iterations):
        neighbor = _neighbor_by_edge_swap(G, best)
        if neighbor is None:
            break
        c = _tree_cost(neighbor, max_children, penalty)
        if c < best_cost:
            best, best_cost = neighbor, c
            history.append(best_cost)
        else:
            # no improvement this step; continue exploring
            continue

    return best, history

def simulated_annealing_spanning_tree(
    G: nx.Graph,
    max_children: int = 3,
    penalty: int = 1000,
    max_iterations: int = 1000,
    initial_temperature: float = 100.0,
    cooling_rate: float = 0.95,
    stop_event=None,
    queue=None,
    return_stats: bool = False,
    initial_tree: nx.Graph = None
):
    """
    Simple SA using edge-swap neighbor generation.
    Defaults aligned with Advanced Mode UI:
      - Temperature=100, Cooling=0.95, Iterations=1000
    """
    random.seed()
    _ensure_weights(G)

    # Start from greedy if not provided
    if initial_tree is None:
        initial_tree, _ = greedy_spanning_tree(G, max_children, penalty)

    current = initial_tree.copy()
    current_cost = _tree_cost(current, max_children, penalty)
    best = current.copy()
    best_cost = current_cost

    T = float(initial_temperature)
    history = [current_cost]

    for it in range(int(max_iterations)):
        if stop_event is not None and getattr(stop_event, 'is_set', lambda: False)():
            break

        neighbor = _neighbor_by_edge_swap(G, current)
        if neighbor is None:
            break

        cost_n = _tree_cost(neighbor, max_children, penalty)
        delta = cost_n - current_cost

        accept = False
        if delta <= 0:
            accept = True
        else:
            if T > 1e-12:
                prob = min(1.0, pow(2.718281828, -delta / T))
                accept = random.random() < prob

        if accept:
            current = neighbor
            current_cost = cost_n
            if current_cost < best_cost:
                best, best_cost = current, current_cost

        history.append(best_cost)

        # Progress / cooling
        if queue is not None and it % max(1, int(max_iterations // 100)) == 0:
            try:
                queue.put(("progress", min(100, (it / max_iterations) * 100)))
                queue.put(("temp", f"{T:.6f}"))
                queue.put(("cost", current_cost))
            except Exception:
                pass

        T = max(1e-9, T * cooling_rate)
        if T < 1e-6:
            break

    if return_stats:
        return best, best_cost, history
    return best, best_cost

# -------------------------------
# Orchestration
# -------------------------------

def compute_score(
    *,
    cost: float,
    violations: int = 0,
    time_s: float,
    memory_mb: Optional[float] = None,
    cost_ref: float,
    time_ref: float = 0.1,
    memory_ref: float = 100.0,
    w_cost: float = 0.7,
    w_time: float = 0.2,
    w_mem: float = 0.1,
    lambda_penalty: float = 10.0,
    mapping: str = "exp",
) -> Dict[str, float]:
    """MAUT-based score with exponential utility and log terms for time/memory.

    Returns a dict with 'score' (0-100), 'L', 'cost_eff', and 'weights'.
    """
    if cost_ref <= 0 or time_ref <= 0 or (memory_mb is not None and memory_ref <= 0):
        raise ValueError("I riferimenti (cost_ref, time_ref, memory_ref) devono essere > 0.")

    if memory_mb is None:
        total = w_cost + w_time
        w_cost_eff = w_cost / total
        w_time_eff = w_time / total
        w_mem_eff = 0.0
    else:
        total = w_cost + w_time + w_mem
        w_cost_eff = w_cost / total
        w_time_eff = w_time / total
        w_mem_eff = w_mem / total

    cost_eff = float(cost) + float(lambda_penalty) * float(max(0, int(violations)))
    comp_cost = cost_eff / float(cost_ref)
    comp_time = log(1.0 + max(float(time_s), 0.0) / float(time_ref))

    L = w_cost_eff * comp_cost + w_time_eff * comp_time
    if memory_mb is not None:
        comp_mem = log(1.0 + max(float(memory_mb), 0.0) / float(memory_ref))
        L += w_mem_eff * comp_mem

    if mapping == "exp":
        score = 100.0 * exp(-L)
    elif mapping == "reciprocal":
        score = 100.0 / (1.0 + L)
    else:
        raise ValueError("mapping deve essere 'exp' o 'reciprocal'.")

    return {
        "score": float(score),
        "L": float(L),
        "cost_eff": float(cost_eff),
        "weights": {"cost": w_cost_eff, "time": w_time_eff, "memory": w_mem_eff},
    }


def evaluate_solution(solution: Dict[str, Any], reference_values: Dict[str, Any]) -> float:
    """Wrapper to compute_score using dict inputs.

    Expected solution keys:
      - cost, execution_time, memory (KB), violations
    Expected reference_values keys (preferred):
      - cost_ref, time_ref, memory_ref (MB)
    Backward-compat: if only max_cost/max_time/max_memory (KB) exist, they are converted to refs.
    """
    cost = float(solution.get("cost", 0.0) or 0.0)
    tsec = float(solution.get("execution_time", 0.0) or 0.0)
    mem_kb = solution.get("memory", None)
    mem_mb = None
    if mem_kb is not None:
        try:
            mem_mb = float(mem_kb) / 1024.0
        except Exception:
            mem_mb = None

    # References: prefer *_ref; else fall back to max_* with conversions
    if "cost_ref" in reference_values:
        cost_ref = float(reference_values["cost_ref"]) or max(1.0, cost)
    else:
        cost_ref = float(reference_values.get("max_cost", max(1.0, cost)))

    if "time_ref" in reference_values:
        time_ref = float(reference_values["time_ref"]) or max(0.001, tsec)
    else:
        time_ref = float(reference_values.get("max_time", max(0.001, tsec)))

    memory_ref = None
    if "memory_ref" in reference_values:
        memory_ref = float(reference_values["memory_ref"])  # already MB
    elif "max_memory" in reference_values:
        try:
            memory_ref = float(reference_values["max_memory"]) / 1024.0
        except Exception:
            memory_ref = None

    violations = int(solution.get("violations", 0) or 0)

    res = compute_score(
        cost=cost,
        violations=violations,
        time_s=tsec,
        memory_mb=mem_mb,
        cost_ref=cost_ref,
        time_ref=time_ref,
        memory_ref=(memory_ref if memory_ref is not None else 100.0),
        w_cost=0.7,
        w_time=0.2,
        w_mem=0.1,
        lambda_penalty=10.0,
        mapping="exp",
    )
    return round(float(res["score"]), 2)

def count_constraint_violations(tree: nx.Graph, max_children: int) -> int:
    """Return total degree excess across nodes (simple violation count)."""
    deg = dict(tree.degree())
    return int(sum(max(0, d - max_children) for d in deg.values()))

def test_instance(
    G: nx.Graph,
    max_children: int,
    penalty: int,
    instance_name: str = "",
    stop_event=None,
    queue=None,
    progress_info=None,
    sa_initial_temperature: float = None,
    sa_cooling_rate: float = None,
    sa_max_iterations: int = None
) -> Dict[str, Any]:
    """
    Run Greedy → Local Search → SA on a single graph instance.
    If SA parameters are provided, use them; otherwise use defaults.
    """
    _ensure_weights(G)

    results: Dict[str, Any] = {}

    # Greedy (measure time + memory using tracemalloc peak)
    tracemalloc.start()
    t0 = time.perf_counter()
    greedy_tree, greedy_cost = greedy_spanning_tree(G, max_children, penalty)
    greedy_time = time.perf_counter() - t0
    _cur, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    greedy_mem_kb = round((_peak or 0) / 1024.0, 2)
    greedy_viol = count_constraint_violations(greedy_tree, max_children)
    results["Greedy"] = {
        "tree": greedy_tree,
        "cost": greedy_cost,
        "time": greedy_time,
        "memory": greedy_mem_kb,
        "violations": greedy_viol
    }

    # Local Search from Greedy
    tracemalloc.start()
    t0 = time.perf_counter()
    local_tree, local_hist = adaptive_neighborhood_local_search(G, greedy_tree, max_children, penalty, max_iterations=500)
    local_cost = _tree_cost(local_tree, max_children, penalty)
    local_time = time.perf_counter() - t0
    _cur, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    local_mem_kb = round((_peak or 0) / 1024.0, 2)
    local_viol = count_constraint_violations(local_tree, max_children)
    results["Local"] = {
        "tree": local_tree,
        "cost": local_cost,
        "time": local_time,
        "memory": local_mem_kb,
        "violations": local_viol,
        "history": local_hist
    }

    # SA from Local (or Greedy if identical)
    tracemalloc.start()
    t0 = time.perf_counter()
    T0 = 100.0 if sa_initial_temperature is None else float(sa_initial_temperature)
    alpha = 0.95 if sa_cooling_rate is None else float(sa_cooling_rate)
    iters = 1000 if sa_max_iterations is None else int(sa_max_iterations)
    sa_tree, sa_cost, sa_hist = simulated_annealing_spanning_tree(
        G, max_children, penalty,
        max_iterations=iters,
        initial_temperature=T0,
        cooling_rate=alpha,
        stop_event=stop_event,
        return_stats=True,
        initial_tree=local_tree
    )
    sa_time = time.perf_counter() - t0
    _cur, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sa_mem_kb = round((_peak or 0) / 1024.0, 2)
    sa_viol = count_constraint_violations(sa_tree, max_children)
    results["SA"] = {
        "tree": sa_tree,
        "cost": sa_cost,
        "time": sa_time,
        "memory": sa_mem_kb,
        "violations": sa_viol,
        "history": sa_hist
    }

    # Backward-compatible flat keys expected by GUI and tests
    results.update({
        # Greedy
        "greedy_tree": greedy_tree,
        "greedy_cost": float(greedy_cost),
        "greedy_time": float(greedy_time),
    "greedy_memory": float(greedy_mem_kb),
        "greedy_violations": int(greedy_viol),
        "greedy_score_history": [float(greedy_cost)],

        # Local
        "local_tree": local_tree,
        "local_cost": float(local_cost),
        "local_time": float(local_time),
    "local_memory": float(local_mem_kb),
        "local_violations": int(local_viol),
        "local_score_history": [float(x) for x in local_hist],

        # SA
        "sa_tree": sa_tree,
        "sa_cost": float(sa_cost),
        "sa_time": float(sa_time),
    "sa_memory": float(sa_mem_kb),
        "sa_violations": int(sa_viol),
        "sa_score_history": [float(x) for x in sa_hist],
    })

    return results

# Backward-compat alias
def run_instance(*args, **kwargs):
    return test_instance(*args, **kwargs)

# Basic cost function exposed for compatibility
def calculate_cost_base(spanning_tree: nx.Graph, max_children: int, penalty: int, counter=None) -> float:
    return _tree_cost(spanning_tree, max_children, penalty)
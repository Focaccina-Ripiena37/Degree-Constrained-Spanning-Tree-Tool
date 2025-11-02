import networkx as nx

from app.utils_core import generate_connected_random_graph
from app.algorithms import count_constraint_violations


def test_generate_connected_random_graph_basic():
    G = generate_connected_random_graph(10, p=0.2)
    assert isinstance(G, nx.Graph)
    # Graph should be connected
    assert nx.is_connected(G)
    # All edges should have positive integer weights
    for u, v, data in G.edges(data=True):
        w = data.get('weight')
        assert isinstance(w, int)
        assert 1 <= w <= 10


def test_generate_connected_random_graph_small_n():
    # n < 2 should return a single-node graph
    G = generate_connected_random_graph(1, p=0.5)
    assert len(G.nodes()) == 1
    assert len(G.edges()) == 0


def test_count_constraint_violations_simple():
    # Build a small tree where node 0 has degree 3
    G = nx.Graph()
    G.add_weighted_edges_from([
        (0, 1, 1),
        (0, 2, 1),
        (0, 3, 1),
    ])
    # With k=2, node 0 exceeds by 1
    v = count_constraint_violations(G, max_children=2)
    assert v == 1

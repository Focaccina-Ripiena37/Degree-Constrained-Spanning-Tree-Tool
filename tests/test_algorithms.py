import networkx as nx

from app.algorithms import run_instance, count_constraint_violations


def make_simple_graph(n=5):
    G = nx.Graph()
    for i in range(n):
        G.add_node(i)
    # connect as a simple path with unit weights
    for i in range(n-1):
        G.add_edge(i, i+1, weight=1)
    # add some extra edges
    if n >= 4:
        G.add_edge(0, 2, weight=2)
        G.add_edge(1, 3, weight=2)
    return G


def test_test_instance_returns_minimal_results():
    G = make_simple_graph(6)
    res = run_instance(G, max_children=3, penalty=1000, instance_name="test")

    assert isinstance(res, dict)
    assert "greedy_tree" in res
    T = res["greedy_tree"]
    assert isinstance(T, nx.Graph)
    # Tree should have n-1 edges
    assert len(T.edges()) == len(G.nodes()) - 1

    # Costs should be numeric for greedy and local
    assert isinstance(res.get("greedy_cost"), (int, float))
    assert isinstance(res.get("local_cost"), (int, float))

    # Violations calculation should not crash
    v = count_constraint_violations(T, 3)
    assert isinstance(v, int)

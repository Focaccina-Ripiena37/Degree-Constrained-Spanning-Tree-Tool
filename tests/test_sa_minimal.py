import networkx as nx

from app.algorithms import run_instance


def test_simulated_annealing_minimal_tree_properties():
    # Small connected graph with random weights
    G = nx.cycle_graph(6)
    # add one chord to offer alternatives
    G.add_edge(0, 3, weight=2)
    for u, v in G.edges():
        if 'weight' not in G[u][v]:
            G[u][v]['weight'] = 1

    res = run_instance(
        G,
        max_children=3,
        penalty=1000,
        instance_name="sa-min",
        sa_initial_temperature=10.0,
        sa_cooling_rate=0.9,
        sa_max_iterations=60,
    )

    sa = res["SA"]
    T = sa["tree"]
    assert isinstance(T, nx.Graph)
    # Must be a spanning tree
    assert T.number_of_nodes() == G.number_of_nodes()
    assert T.number_of_edges() == G.number_of_nodes() - 1
    assert nx.is_connected(T)

    # Metrics sanity
    assert isinstance(sa.get("cost"), (int, float))
    assert isinstance(sa.get("time"), (int, float))
    assert isinstance(sa.get("violations"), int)
    hist = sa.get("history")
    assert isinstance(hist, list) and len(hist) >= 1

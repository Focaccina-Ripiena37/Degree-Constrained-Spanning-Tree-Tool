import networkx as nx

from app.algorithms import run_instance


def test_run_instance_contract():
    G = nx.path_graph(5)
    # add weights
    for u, v in G.edges():
        G[u][v]['weight'] = 1
    res = run_instance(G, max_children=3, penalty=1000, instance_name="contract")

    # Nested keys
    assert isinstance(res.get("Greedy"), dict)
    assert isinstance(res.get("Local"), dict)
    assert isinstance(res.get("SA"), dict)
    for k in ("Greedy", "Local", "SA"):
        d = res[k]
        assert "tree" in d and d["tree"] is not None
        assert isinstance(d.get("cost"), (int, float))
        assert isinstance(d.get("time"), (int, float))
        assert isinstance(d.get("violations"), int)

    # Flat keys
    flat = [
        "greedy_tree","greedy_cost","greedy_time","greedy_memory","greedy_violations",
        "local_tree","local_cost","local_time","local_memory","local_violations",
        "sa_tree","sa_cost","sa_time","sa_memory","sa_violations",
    ]
    for key in flat:
        assert key in res

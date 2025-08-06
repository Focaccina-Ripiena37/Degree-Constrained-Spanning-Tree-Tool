#!/usr/bin/env python3
"""
Simplified Parallelization System for DCST Tool.
Educational-friendly implementation with fixed workers and simple rules.

This module replaces the complex adaptive parallelization system with a simple,
understandable approach suitable for intermediate-level students.
"""

import os
import time
import logging
import multiprocessing
import concurrent.futures
from typing import List, Callable, Any, Optional, Tuple

# Simple configuration constants
MAX_WORKERS = 4  # Fixed maximum workers
MIN_ITEMS_FOR_PARALLEL = 5  # Minimum items to use parallelization
SIMPLE_TIMEOUT = 60  # Simple timeout in seconds


def get_simple_worker_count(num_items: int) -> int:
    """
    Simple rule for determining worker count.
    
    Educational Rule:
    - If less than 5 items: use 1 worker (sequential)
    - If 5 or more items: use 2-4 workers based on CPU cores
    
    Args:
        num_items: Number of items to process
        
    Returns:
        int: Number of workers to use (1-4)
    """
    # Rule 1: Sequential for small problems
    if num_items < MIN_ITEMS_FOR_PARALLEL:
        return 1
    
    # Rule 2: Use 2-4 workers for larger problems
    try:
        cpu_cores = os.cpu_count() or 2
        # Simple formula: min(4, max(2, cpu_cores // 2))
        workers = min(MAX_WORKERS, max(2, cpu_cores // 2))
        return workers
    except Exception:
        # Fallback to 2 workers if detection fails
        return 2


def should_use_parallel(num_items: int) -> bool:
    """
    Simple decision function for parallelization.
    
    Educational Rule:
    - Use parallel processing only if we have 5+ items
    - Always fallback to sequential on any issues
    
    Args:
        num_items: Number of items to process
        
    Returns:
        bool: True if should use parallel processing
    """
    return num_items >= MIN_ITEMS_FOR_PARALLEL


def simple_parallel_cost_evaluation(candidate_solutions: List[Any], 
                                   max_children: int, 
                                   penalty: int, 
                                   cost_function: Callable) -> List[float]:
    """
    Simplified parallel cost evaluation with fixed workers.
    
    Educational Implementation:
    1. Check if we should use parallel processing
    2. Use fixed number of workers (2-4)
    3. Simple timeout (60 seconds)
    4. Fallback to sequential on any error
    
    Args:
        candidate_solutions: List of solutions to evaluate
        max_children: Maximum degree constraint
        penalty: Penalty for violations
        cost_function: Function to calculate cost
        
    Returns:
        List[float]: Costs for each solution
    """
    num_candidates = len(candidate_solutions)
    
    # Step 1: Check if we should use parallel processing
    if not should_use_parallel(num_candidates):
        logging.info(f"Using sequential evaluation for {num_candidates} candidates (< {MIN_ITEMS_FOR_PARALLEL})")
        return [cost_function(candidate, max_children, penalty) for candidate in candidate_solutions]
    
    # Step 2: Determine number of workers
    num_workers = get_simple_worker_count(num_candidates)
    logging.info(f"Using parallel evaluation with {num_workers} workers for {num_candidates} candidates")
    
    # Step 3: Try parallel processing with simple timeout
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            futures = [
                executor.submit(cost_function, candidate, max_children, penalty)
                for candidate in candidate_solutions
            ]
            
            # Collect results with simple timeout
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=SIMPLE_TIMEOUT):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logging.warning(f"Individual cost evaluation failed: {e}")
                    # Use a high penalty cost for failed evaluations
                    results.append(float('inf'))
            
            return results
            
    except concurrent.futures.TimeoutError:
        logging.warning(f"Parallel cost evaluation timed out after {SIMPLE_TIMEOUT}s. Using sequential fallback.")
        return _sequential_fallback(candidate_solutions, max_children, penalty, cost_function)
    except Exception as e:
        logging.warning(f"Parallel cost evaluation failed: {e}. Using sequential fallback.")
        return _sequential_fallback(candidate_solutions, max_children, penalty, cost_function)


def simple_parallel_local_search(G, initial_tree, max_degree, penalty, 
                                stop_event=None, queue=None) -> Tuple[Any, int, List]:
    """
    Simplified parallel local search with fixed workers.
    
    Educational Implementation:
    1. Check graph size to decide on parallelization
    2. Use fixed number of workers
    3. Simple timeout and error handling
    4. Fallback to sequential version
    
    Args:
        G: NetworkX graph
        initial_tree: Initial spanning tree
        max_degree: Maximum degree constraint
        penalty: Penalty for violations
        stop_event: Optional stop event
        queue: Optional progress queue
        
    Returns:
        Tuple: (best_tree, cost_calls, score_history)
    """
    graph_size = len(G.nodes())
    
    # Step 1: Simple decision based on graph size
    if graph_size < 20:  # Small graphs use sequential
        logging.info(f"Using sequential local search for small graph ({graph_size} nodes)")
        return _sequential_local_search_fallback(G, initial_tree, max_degree, penalty, stop_event, queue)
    
    # Step 2: Determine workers for larger graphs
    num_workers = get_simple_worker_count(graph_size)
    
    if queue:
        queue.put(("log", (f"🔧 Using simplified parallel local search with {num_workers} workers", "info")))
    
    # Step 3: Try parallel processing with simple approach
    try:
        # Import the sequential version for fallback
        from .algorithms import adaptive_neighborhood_local_search
        
        # For educational simplicity, we'll use a simple parallel approach:
        # Run multiple independent local searches and take the best result
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit multiple independent searches
            futures = []
            for i in range(num_workers):
                future = executor.submit(
                    _single_local_search_worker,
                    G, initial_tree, max_degree, penalty, i
                )
                futures.append(future)
            
            # Collect results with timeout
            best_tree = initial_tree
            total_calls = 0
            best_score_history = []
            best_cost = float('inf')
            
            for future in concurrent.futures.as_completed(futures, timeout=SIMPLE_TIMEOUT):
                try:
                    tree, calls, history, cost = future.result()
                    total_calls += calls
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_tree = tree
                        best_score_history = history
                        
                except Exception as e:
                    logging.warning(f"Individual local search worker failed: {e}")
                    continue
            
            if queue:
                queue.put(("log", (f"✅ Parallel local search completed with cost {best_cost}", "success")))
            
            return best_tree, total_calls, best_score_history
            
    except concurrent.futures.TimeoutError:
        logging.warning(f"Parallel local search timed out after {SIMPLE_TIMEOUT}s. Using sequential fallback.")
        return _sequential_local_search_fallback(G, initial_tree, max_degree, penalty, stop_event, queue)
    except Exception as e:
        logging.warning(f"Parallel local search failed: {e}. Using sequential fallback.")
        return _sequential_local_search_fallback(G, initial_tree, max_degree, penalty, stop_event, queue)


def _sequential_fallback(candidate_solutions: List[Any], max_children: int, 
                        penalty: int, cost_function: Callable) -> List[float]:
    """Simple sequential fallback for cost evaluation."""
    logging.info("Using sequential fallback for cost evaluation")
    return [cost_function(candidate, max_children, penalty) for candidate in candidate_solutions]


def _sequential_local_search_fallback(G, initial_tree, max_degree, penalty, stop_event, queue):
    """Simple sequential fallback for local search."""
    try:
        from .algorithms import adaptive_neighborhood_local_search
        if queue:
            queue.put(("log", ("🔄 Using sequential local search fallback", "info")))
        return adaptive_neighborhood_local_search(G, initial_tree, max_degree, penalty, stop_event, queue)
    except Exception as e:
        logging.error(f"Sequential fallback also failed: {e}")
        # Return the initial tree as last resort
        return initial_tree, 0, []


def _single_local_search_worker(G, initial_tree, max_degree, penalty, worker_id):
    """
    Single worker for parallel local search.
    
    This is a simplified worker that runs a basic local search.
    Each worker starts from the same initial tree but uses different
    random seeds for variety.
    """
    import random
    import networkx as nx
    
    # Set different random seed for each worker
    random.seed(worker_id * 42)
    
    try:
        # Import cost calculation function
        from .algorithms import calculate_cost_local
        
        current_tree = initial_tree.copy()
        current_cost = calculate_cost_local(current_tree, max_degree, penalty)
        
        cost_calls = 1
        score_history = [(0, {'score': current_cost})]
        
        # Simple local search: try a few random edge swaps
        max_iterations = 50  # Fixed number of iterations for simplicity
        
        for iteration in range(max_iterations):
            # Get edges not in current tree
            tree_edges = set(current_tree.edges())
            graph_edges = set(G.edges())
            non_tree_edges = list(graph_edges - tree_edges)
            
            if not non_tree_edges:
                break
            
            # Try a random edge swap
            edge_to_add = random.choice(non_tree_edges)
            
            # Add edge and find cycle
            temp_tree = current_tree.copy()
            temp_tree.add_edge(*edge_to_add)
            
            # Find cycle and remove random edge from it
            try:
                cycle = nx.find_cycle(temp_tree)
                if len(cycle) > 1:
                    # Remove a random edge from the cycle (except the one we just added)
                    cycle_edges = [(u, v) for u, v, _ in cycle]
                    removable_edges = [e for e in cycle_edges if e != edge_to_add and (e[1], e[0]) != edge_to_add]
                    
                    if removable_edges:
                        edge_to_remove = random.choice(removable_edges)
                        temp_tree.remove_edge(*edge_to_remove)
                        
                        # Check if this is better
                        new_cost = calculate_cost_local(temp_tree, max_degree, penalty)
                        cost_calls += 1
                        
                        if new_cost < current_cost:
                            current_tree = temp_tree
                            current_cost = new_cost
                            score_history.append((iteration + 1, {'score': current_cost}))
                            
            except nx.NetworkXNoCycle:
                # No cycle found, skip this iteration
                continue
            except Exception:
                # Any other error, skip this iteration
                continue
        
        return current_tree, cost_calls, score_history, current_cost
        
    except Exception as e:
        logging.warning(f"Local search worker {worker_id} failed: {e}")
        # Return initial values
        return initial_tree, 0, [], float('inf')


def get_parallelization_info() -> dict:
    """
    Get information about the simplified parallelization system.
    
    Returns:
        dict: Information about the parallelization configuration
    """
    try:
        cpu_cores = os.cpu_count() or 2
    except Exception:
        cpu_cores = 2
    
    return {
        'system_type': 'simplified',
        'max_workers': MAX_WORKERS,
        'cpu_cores': cpu_cores,
        'min_items_for_parallel': MIN_ITEMS_FOR_PARALLEL,
        'timeout_seconds': SIMPLE_TIMEOUT,
        'recommended_workers': get_simple_worker_count(10),  # Example with 10 items
        'description': 'Educational-friendly fixed-worker parallelization'
    }

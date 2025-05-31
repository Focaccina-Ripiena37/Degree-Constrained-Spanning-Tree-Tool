# app/algorithms.py - Algoritmi principali per l'applicazione DCST

#==============================================================================
#                           1. IMPORTAZIONI
#==============================================================================

# Importazioni della libreria standard
import gc
import os
import math
import time
import heapq
import random
import logging
import threading
from typing import Dict, Any

# Importazioni di terze parti
import psutil
import numpy as np
import networkx as nx
import concurrent.futures
import multiprocessing
from functools import partial

# Importazioni locali per configurazione
from .config import (
    # Adaptive scaling constants
    MAX_WORKERS_CONSERVATIVE, MAX_WORKERS_FALLBACK, MIN_CORES_FOR_OS,
    WORKSTATION_MIN_CORES, WORKSTATION_MIN_RAM, DESKTOP_MIN_CORES, DESKTOP_MIN_RAM,
    WORKSTATION_SAFETY_MARGIN, DESKTOP_SAFETY_MARGIN, LAPTOP_SAFETY_MARGIN,
    WORKSTATION_RAM_EFFICIENCY, DESKTOP_RAM_EFFICIENCY, LAPTOP_RAM_EFFICIENCY,
    ENABLE_ADAPTIVE_SCALING, ADAPTIVE_SCALING_MIN_CORES, ADAPTIVE_SCALING_MIN_RAM,
    ENV_FORCE_CONSERVATIVE_MODE, ENV_MAX_WORKERS_OVERRIDE, ENV_SAFETY_MARGIN_OVERRIDE,
    # Other constants
    DEFAULT_SAFETY_MARGIN, MIN_RAM_PER_WORKER, CPU_CHECK_INTERVAL,
    MIN_MEMORY_GB, LOW_MEMORY_GB, LIMITED_MEMORY_GB,
    DEFAULT_PENALTY, DEFAULT_MAX_CHILDREN,
    ENV_OMP_THREADS, ENV_MKL_THREADS, ENV_NUMEXPR_THREADS, ENV_OPENBLAS_THREADS,
    DEFAULT_PLOT_DIR_NAME, FALLBACK_PLOT_PREFIX, MAX_PLOT_DIRECTORIES,
    LARGE_GRAPH_THRESHOLD, LS_MAX_ITERATIONS, SA_INITIAL_TEMPERATURE,
    SA_COOLING_RATE, SA_MIN_TEMPERATURE, SA_LARGE_INSTANCE_MIN_TEMP,
    SA_LARGE_INSTANCE_COOLING, PARALLEL_COST_EVAL_TIMEOUT_PER_CANDIDATE,
    PARALLEL_COST_EVAL_TIMEOUT_MAX, INDIVIDUAL_TASK_TIMEOUT,
    EMERGENCY_CLEANUP_CPU_THRESHOLD
)

# Memory profiling for precise memory measurement
try:
    from memory_profiler import memory_usage
    MEMORY_PROFILER_AVAILABLE = True
    logging.info("memory_profiler available for precise memory measurement")
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    logging.warning("memory_profiler not available, falling back to psutil for memory measurement")

# All operations use CPU-only optimizations for maximum stability

#==============================================================================
#                           2. DEFINIZIONE DELLE VARIABILI GLOBALI
#==============================================================================
greedy_cost_calls = [0]
local_search_cost_calls = [0]
sa_cost_calls = [0]

# Global resource management variables
_last_cpu_check = 0
_cpu_check_interval = CPU_CHECK_INTERVAL
_current_worker_count = None
_resource_safety_margin = DEFAULT_SAFETY_MARGIN

#==============================================================================
#                           4. INIZIALIZZAZIONE DELL'ISTANZA DI TEST
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

    # Only log if logging is properly configured
    try:
        logging.info("Test instance initialized successfully")
    except:
        pass  # Ignore logging errors during import
    return test_instance

# Initialize test instance only if not already done
if not test_instance.get('graph') or len(test_instance['graph'].nodes()) == 0:
    initialize_test_instance()

#==============================================================================
#                           4. ADAPTIVE RESOURCE MANAGEMENT
#==============================================================================

def detect_system_resources():
    """
    Detect available system resources (CPU cores and RAM) with error handling.

    Returns:
        tuple: (cpu_cores, total_ram_gb, available_ram_gb)
    """
    try:
        # Get CPU information
        cpu_cores = psutil.cpu_count(logical=True)
        if cpu_cores is None:
            cpu_cores = multiprocessing.cpu_count()

        # Get memory information
        memory = psutil.virtual_memory()
        total_ram_gb = memory.total / (1024**3)  # Convert to GB
        available_ram_gb = memory.available / (1024**3)  # Convert to GB

        logging.info(f"System resources detected: {cpu_cores} CPU cores, "
                    f"{total_ram_gb:.1f}GB total RAM, {available_ram_gb:.1f}GB available RAM")

        return cpu_cores, total_ram_gb, available_ram_gb

    except Exception as e:
        logging.warning(f"Failed to detect system resources: {e}. Using fallback values.")
        # Fallback to conservative values
        return 2, 4.0, 2.0

def classify_system_type(cpu_cores, available_ram_gb):
    """
    Classify the system type based on CPU cores and available RAM.

    Args:
        cpu_cores (int): Number of CPU cores
        available_ram_gb (float): Available RAM in GB

    Returns:
        tuple: (system_type, safety_margin, ram_efficiency)
    """
    # Check for workstation-class system
    if cpu_cores >= WORKSTATION_MIN_CORES and available_ram_gb >= WORKSTATION_MIN_RAM:
        return "workstation", WORKSTATION_SAFETY_MARGIN, WORKSTATION_RAM_EFFICIENCY

    # Check for desktop-class system
    elif cpu_cores >= DESKTOP_MIN_CORES and available_ram_gb >= DESKTOP_MIN_RAM:
        return "desktop", DESKTOP_SAFETY_MARGIN, DESKTOP_RAM_EFFICIENCY

    # Default to laptop/modest system
    else:
        return "laptop", LAPTOP_SAFETY_MARGIN, LAPTOP_RAM_EFFICIENCY

def check_user_overrides():
    """
    Check for user-specified overrides via environment variables.

    Returns:
        dict: Dictionary with override values (None if not set)
    """
    overrides = {
        'force_conservative': os.environ.get(ENV_FORCE_CONSERVATIVE_MODE, '').lower() in ('1', 'true', 'yes'),
        'max_workers': None,
        'safety_margin': None
    }

    # Check for max workers override
    try:
        max_workers_env = os.environ.get(ENV_MAX_WORKERS_OVERRIDE)
        if max_workers_env:
            overrides['max_workers'] = max(1, int(max_workers_env))
    except (ValueError, TypeError):
        logging.warning(f"Invalid {ENV_MAX_WORKERS_OVERRIDE} value: {max_workers_env}")

    # Check for safety margin override
    try:
        safety_margin_env = os.environ.get(ENV_SAFETY_MARGIN_OVERRIDE)
        if safety_margin_env:
            margin = float(safety_margin_env)
            if 0.1 <= margin <= 1.0:
                overrides['safety_margin'] = margin
            else:
                logging.warning(f"Safety margin must be between 0.1 and 1.0, got: {margin}")
    except (ValueError, TypeError):
        logging.warning(f"Invalid {ENV_SAFETY_MARGIN_OVERRIDE} value: {safety_margin_env}")

    return overrides

def calculate_optimal_workers(safety_margin=None, min_ram_per_worker=None, max_workers=None):
    """
    ADAPTIVE SCALING: Calculate optimal number of worker processes based on system resources.
    Automatically scales from conservative (laptops) to aggressive (workstations).

    Args:
        safety_margin (float): Safety margin for resource usage (0.0-1.0)
        min_ram_per_worker (float): Minimum RAM per worker in GB
        max_workers (int): Maximum number of workers (optional override)

    Returns:
        int: Optimal number of worker processes (adaptively limited based on system type)
    """
    global _current_worker_count, _resource_safety_margin

    try:
        cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()

        # Check user overrides first
        user_overrides = check_user_overrides()

        # Force conservative mode if requested
        if user_overrides['force_conservative']:
            logging.info("CONSERVATIVE MODE: Forced via environment variable")
            safety_margin = LAPTOP_SAFETY_MARGIN
            max_allowed_workers = MAX_WORKERS_CONSERVATIVE
            system_type = "conservative_override"
        else:
            # ADAPTIVE SCALING: Classify system and get appropriate parameters
            if not ENABLE_ADAPTIVE_SCALING or cpu_cores < ADAPTIVE_SCALING_MIN_CORES or available_ram_gb < ADAPTIVE_SCALING_MIN_RAM:
                # Fall back to conservative mode for very modest systems
                system_type = "conservative_fallback"
                safety_margin = LAPTOP_SAFETY_MARGIN if safety_margin is None else safety_margin
                max_allowed_workers = MAX_WORKERS_CONSERVATIVE
            else:
                # Use adaptive classification
                system_type, adaptive_safety_margin, ram_efficiency = classify_system_type(cpu_cores, available_ram_gb)

                # Use adaptive safety margin if not explicitly provided
                if safety_margin is None:
                    safety_margin = adaptive_safety_margin

                # Calculate dynamic maximum workers based on system capabilities
                # Always leave MIN_CORES_FOR_OS cores for the OS
                max_allowed_workers = max(1, cpu_cores - MIN_CORES_FOR_OS)

                # Additional RAM-based limit for workstations
                if system_type == "workstation":
                    ram_based_max = int((available_ram_gb * ram_efficiency) / (min_ram_per_worker or MIN_RAM_PER_WORKER))
                    max_allowed_workers = min(max_allowed_workers, ram_based_max)

        # Apply user overrides
        if user_overrides['safety_margin'] is not None:
            safety_margin = user_overrides['safety_margin']
            logging.info(f"Using user-specified safety margin: {safety_margin}")

        if user_overrides['max_workers'] is not None:
            max_allowed_workers = min(max_allowed_workers, user_overrides['max_workers'])
            logging.info(f"Using user-specified max workers: {user_overrides['max_workers']}")

        # Use defaults if not provided
        if min_ram_per_worker is None:
            min_ram_per_worker = MIN_RAM_PER_WORKER

        # Update global safety margin
        _resource_safety_margin = safety_margin

        # Calculate workers based on CPU with adaptive safety margin
        cpu_based_workers = max(1, int(cpu_cores * safety_margin))

        # Calculate workers based on RAM with adaptive safety margin
        usable_ram = max(MIN_MEMORY_GB, available_ram_gb * 0.8)  # Use 80% of available RAM
        ram_based_workers = max(1, int((usable_ram * safety_margin) / min_ram_per_worker))

        # Take the minimum to avoid resource contention
        optimal_workers = min(cpu_based_workers, ram_based_workers, max_allowed_workers)

        # Apply user-specified maximum limit if provided
        if max_workers is not None:
            optimal_workers = min(optimal_workers, max_workers)

        # Ensure at least 1 worker
        optimal_workers = max(1, optimal_workers)

        # Emergency fallback for very low-resource systems
        if available_ram_gb < LIMITED_MEMORY_GB:
            optimal_workers = MAX_WORKERS_FALLBACK
            logging.warning(f"calculate_optimal_workers: Very low RAM detected ({available_ram_gb:.1f}GB). Emergency fallback to {MAX_WORKERS_FALLBACK} worker.")
        elif available_ram_gb < 8.0 and optimal_workers > 2:
            optimal_workers = 2
            logging.warning(f"calculate_optimal_workers: Limited RAM detected ({available_ram_gb:.1f}GB). Limiting to 2 workers max.")

        _current_worker_count = optimal_workers

        logging.info(f"ADAPTIVE SCALING: {system_type.upper()} system detected")
        logging.info(f"Optimal workers calculated: {optimal_workers} "
                    f"(CPU-based: {cpu_based_workers}, RAM-based: {ram_based_workers}, "
                    f"Max allowed: {max_allowed_workers}, Safety margin: {safety_margin:.1%})")
        logging.info(f"System specs: {cpu_cores} cores, {available_ram_gb:.1f}GB available RAM")

        return optimal_workers

    except Exception as e:
        import traceback
        logging.warning(f"calculate_optimal_workers: Failed to calculate optimal workers: {e}")
        logging.debug(f"calculate_optimal_workers: Full traceback: {traceback.format_exc()}")
        _current_worker_count = MAX_WORKERS_FALLBACK
        return MAX_WORKERS_FALLBACK

def monitor_cpu_usage():
    """
    Monitor current CPU usage and return current percentage.

    Returns:
        float: Current CPU usage percentage (0-100)
    """
    global _last_cpu_check, _cpu_check_interval

    try:
        current_time = time.time()

        # Throttle CPU checks to avoid overhead
        if current_time - _last_cpu_check < _cpu_check_interval:
            return psutil.cpu_percent()

        _last_cpu_check = current_time

        # Get CPU usage with a short interval for accuracy
        cpu_usage = psutil.cpu_percent(interval=0.1)

        return cpu_usage

    except Exception as e:
        logging.warning(f"Failed to monitor CPU usage: {e}")
        return 50.0  # Conservative fallback

def get_adaptive_max_workers_for_operation(operation_type="general", base_workers=None):
    """
    Get adaptive maximum workers for specific operations based on system type.

    Args:
        operation_type (str): Type of operation ("cost_eval", "edge_swap", "general")
        base_workers (int): Base number of workers (if None, uses current optimal)

    Returns:
        int: Maximum workers allowed for this operation
    """
    if base_workers is None:
        base_workers = _current_worker_count or calculate_optimal_workers()

    # Get system classification
    try:
        cpu_cores, _, available_ram_gb = detect_system_resources()
        system_type, _, _ = classify_system_type(cpu_cores, available_ram_gb)

        # Conservative limits for specific operations
        if operation_type == "cost_eval":
            if system_type == "workstation":
                return min(base_workers, max(4, cpu_cores // 2))  # Up to half cores or 4, whichever is higher
            elif system_type == "desktop":
                return min(base_workers, 3)  # Up to 3 workers for desktops
            else:
                return min(base_workers, 2)  # Conservative for laptops

        elif operation_type == "edge_swap":
            if system_type == "workstation":
                return min(base_workers, max(3, cpu_cores // 3))  # Up to 1/3 cores or 3, whichever is higher
            elif system_type == "desktop":
                return min(base_workers, 2)  # Up to 2 workers for desktops
            else:
                return 1  # Single worker for laptops (edge swap is memory intensive)

        else:  # general
            return base_workers

    except Exception as e:
        logging.warning(f"get_adaptive_max_workers_for_operation: Failed to get adaptive limits: {e}")
        # Fallback to conservative limits
        if operation_type == "cost_eval":
            return min(base_workers or 2, 2)
        elif operation_type == "edge_swap":
            return 1
        else:
            return base_workers or 1

def adaptive_worker_adjustment(current_workers, cpu_threshold=90.0):
    """
    Dynamically adjust worker count based on current CPU usage.

    Args:
        current_workers (int): Current number of workers
        cpu_threshold (float): CPU usage threshold for throttling

    Returns:
        int: Adjusted number of workers
    """
    try:
        cpu_usage = monitor_cpu_usage()

        if cpu_usage > cpu_threshold:
            # Reduce workers if CPU usage is too high
            adjusted_workers = max(1, current_workers - 1)
            logging.warning(f"adaptive_worker_adjustment: High CPU usage detected ({cpu_usage:.1f}%). "
                          f"Reducing workers from {current_workers} to {adjusted_workers}")
            return adjusted_workers
        elif cpu_usage < cpu_threshold * 0.6 and current_workers < _current_worker_count:
            # Increase workers if CPU usage is low and we're below optimal
            adjusted_workers = min(_current_worker_count, current_workers + 1)
            logging.info(f"adaptive_worker_adjustment: Low CPU usage detected ({cpu_usage:.1f}%). "
                        f"Increasing workers from {current_workers} to {adjusted_workers}")
            return adjusted_workers

        return current_workers

    except Exception as e:
        logging.warning(f"adaptive_worker_adjustment: Failed to adjust workers: {e}")
        return current_workers



def check_system_stability():
    """
    Check system stability and resource availability before intensive operations.

    Returns:
        tuple: (is_stable, warning_message)
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        available_ram_gb = memory.available / (1024**3)

        warnings = []

        # Check CPU usage
        if cpu_usage > 95.0:
            warnings.append(f"Very high CPU usage: {cpu_usage:.1f}%")
        elif cpu_usage > 85.0:
            warnings.append(f"High CPU usage: {cpu_usage:.1f}%")

        # Check available memory
        if available_ram_gb < 1.0:
            warnings.append(f"Critical memory shortage: {available_ram_gb:.1f}GB available")
        elif available_ram_gb < 2.0:
            warnings.append(f"Low memory: {available_ram_gb:.1f}GB available")

        # Check for system stability
        is_stable = cpu_usage < 90.0 and available_ram_gb > 1.0

        if warnings:
            warning_message = "; ".join(warnings)
            return is_stable, warning_message
        else:
            return True, "System resources are stable"

    except Exception as e:
        logging.warning(f"Failed to check system stability: {e}")
        return False, f"System monitoring failed: {e}"

def safe_execution_wrapper(func, *args, timeout=300, **kwargs):
    """
    Wrapper for safe execution of intensive operations with timeout and resource monitoring.

    Args:
        func: Function to execute
        *args: Arguments for the function
        timeout: Maximum execution time in seconds (default: 5 minutes)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function or raises appropriate exceptions
    """
    import threading

    # Check system stability before starting
    is_stable, message = check_system_stability()
    if not is_stable:
        logging.warning(f"System instability detected: {message}")
        # Continue with reduced parallelization
        if 'max_workers' in kwargs:
            kwargs['max_workers'] = 1

    result = None
    exception = None

    def target():
        nonlocal result, exception
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            exception = e

    # Start execution in a separate thread
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()

    # Wait for completion with timeout
    thread.join(timeout)

    if thread.is_alive():
        logging.error(f"Operation timed out after {timeout} seconds")
        # Force garbage collection to free memory
        gc.collect()
        raise TimeoutError(f"Operation exceeded {timeout} second timeout")

    if exception:
        raise exception

    return result

def emergency_resource_cleanup():
    """
    Emergency cleanup function to free system resources.
    Call this when system becomes unstable.
    """
    try:
        # Force garbage collection
        gc.collect()

        # Log cleanup
        logging.info("Emergency resource cleanup completed")

    except Exception as e:
        logging.warning(f"Emergency cleanup failed: {e}")

def adaptive_timeout_calculation(graph_size, base_timeout=300):
    """
    Calculate adaptive timeout based on graph size and system resources.

    Args:
        graph_size: Number of nodes in the graph
        base_timeout: Base timeout in seconds

    Returns:
        int: Calculated timeout in seconds
    """
    try:
        # Base calculation: larger graphs need more time
        size_factor = max(1.0, graph_size / 100.0)
        calculated_timeout = int(base_timeout * size_factor)

        # Adjust based on available resources
        cpu_cores, _, available_ram_gb = detect_system_resources()

        # Reduce timeout if resources are limited
        if available_ram_gb < 2.0:
            calculated_timeout = min(calculated_timeout, 180)  # Max 3 minutes for low memory
        elif available_ram_gb < 4.0:
            calculated_timeout = min(calculated_timeout, 600)  # Max 10 minutes for limited memory

        # Increase timeout if we have plenty of resources
        if available_ram_gb > 8.0 and cpu_cores > 4:
            calculated_timeout = min(calculated_timeout * 1.5, 1800)  # Max 30 minutes even with good resources

        return max(60, calculated_timeout)  # Minimum 1 minute timeout

    except Exception:
        return base_timeout

#==============================================================================
#                           5. FUNZIONI UNITARIE DI BASE
#==============================================================================
def calculate_cost_base(spanning_tree, max_children, penalty, counter):
    """
    Optimized cost calculation for spanning trees with performance improvements.

    Args:
        spanning_tree: Grafo che rappresenta l'albero di copertura
        max_children: Numero massimo di figli per nodo
        penalty: Penalità per violazione dei vincoli
        counter: Lista contenente il contatore per le chiamate della funzione

    Returns:
        total_cost: Costo totale dell'albero
    """
    counter[0] += 1  # Incrementa il contatore associato all'algoritmo

    # PERFORMANCE OPTIMIZATION: Use more efficient edge weight calculation
    if spanning_tree.number_of_edges() == 0:
        return 0.0

    # Calculate edge weights sum more efficiently
    total_cost = sum(data.get('weight', 1) for _, _, data in spanning_tree.edges(data=True))

    # PERFORMANCE OPTIMIZATION: Pre-calculate degrees to avoid repeated calls
    degrees = dict(spanning_tree.degree())

    # PERFORMANCE OPTIMIZATION: Only check constraint violations if max_children is finite
    if max_children != float('inf'):
        # More efficient constraint violation calculation
        violations = 0
        for node in spanning_tree.nodes():
            # Count children more efficiently by checking degree relationships
            node_degree = degrees[node]
            children_count = 0

            for neighbor in spanning_tree.neighbors(node):
                if degrees[neighbor] < node_degree:
                    children_count += 1

            if children_count > max_children:
                violations += children_count - max_children

        total_cost += penalty * violations

    return total_cost

# Usa la function.partial per creare versioni specifiche per ogni algoritmo
calculate_cost_greedy = partial(calculate_cost_base, counter=greedy_cost_calls)
calculate_cost_local = partial(calculate_cost_base, counter=local_search_cost_calls)
calculate_cost_sa = partial(calculate_cost_base, counter=sa_cost_calls)

# GPU acceleration functions completely removed for system stability
# All cost calculations now use the optimized CPU-only implementation above

#==============================================================================
#                           4.1. FUNZIONI DI PARALLELIZZAZIONE
#==============================================================================

def parallel_cost_evaluation(candidate_solutions, max_children, penalty, cost_function, max_workers=None):
    """
    Evaluate costs of multiple candidate solutions in parallel using adaptive resource management.
    GPU acceleration has been completely removed for system stability.

    Args:
        candidate_solutions: List of spanning trees to evaluate
        max_children: Maximum allowed number of children
        penalty: Penalty for violations
        cost_function: Cost calculation function to use (calculate_cost_local, calculate_cost_sa, etc.)
        max_workers: Maximum number of worker processes (default: adaptive calculation)

    Returns:
        List of costs corresponding to each candidate solution
    """
    if len(candidate_solutions) <= 1:
        # Skip parallelization for single candidates
        if candidate_solutions:
            return [cost_function(candidate_solutions[0], max_children, penalty)]
        return []

    # GPU acceleration completely removed for system stability

    # Use adaptive resource management for worker calculation
    if max_workers is None:
        max_workers = calculate_optimal_workers(safety_margin=0.5, min_ram_per_worker=MIN_RAM_PER_WORKER)

    # ADAPTIVE SCALING: Use operation-specific limits based on system type
    max_workers = get_adaptive_max_workers_for_operation("cost_eval", max_workers)

    # Monitor CPU and adjust workers if needed (more aggressive threshold)
    max_workers = adaptive_worker_adjustment(max_workers, cpu_threshold=80.0)

    # Skip parallelization if only 1 worker is optimal
    if max_workers == 1:
        logging.info("Using sequential evaluation due to resource constraints")
        return [cost_function(candidate, max_children, penalty) for candidate in candidate_solutions]

    try:
        # Check system stability before starting intensive parallel operations
        is_stable, stability_message = check_system_stability()
        if not is_stable:
            logging.warning(f"System instability detected: {stability_message}. Reducing parallelization.")
            max_workers = 1

        # Calculate adaptive timeout based on problem size
        adaptive_timeout = min(60, max(10, len(candidate_solutions) * 2))  # 2 seconds per candidate, max 60s

        logging.debug(f"Starting parallel cost evaluation with {max_workers} workers for {len(candidate_solutions)} candidates (timeout: {adaptive_timeout}s)")

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all cost evaluation tasks (CPU-only)
            futures = [
                executor.submit(cost_function, candidate, max_children, penalty)
                for candidate in candidate_solutions
            ]

            # Collect results as they complete with adaptive timeout and monitoring
            results = []
            completed_count = 0
            start_time = time.time()

            for future in concurrent.futures.as_completed(futures, timeout=adaptive_timeout):
                try:
                    result = future.result(timeout=5)  # Individual task timeout
                    results.append(result)
                    completed_count += 1

                    # Monitor system resources periodically during execution
                    if completed_count % max(1, len(futures) // 4) == 0:
                        cpu_usage = monitor_cpu_usage()
                        elapsed_time = time.time() - start_time

                        if cpu_usage > 95.0:
                            logging.warning(f"Very high CPU usage detected ({cpu_usage:.1f}%) during parallel evaluation")
                            # Consider emergency cleanup if CPU usage is critical
                            if cpu_usage > 98.0:
                                emergency_resource_cleanup()

                        # Check if we're taking too long
                        if elapsed_time > adaptive_timeout * 0.8:
                            logging.warning(f"Parallel evaluation taking longer than expected ({elapsed_time:.1f}s)")

                except concurrent.futures.TimeoutError:
                    logging.warning(f"Individual task timed out during parallel cost evaluation")
                    results.append(float('inf'))
                except Exception as e:
                    logging.warning(f"Parallel cost evaluation failed for one candidate: {e}")
                    # Fallback to sequential calculation for this candidate
                    results.append(float('inf'))

            return results

    except concurrent.futures.TimeoutError:
        logging.warning("Parallel cost evaluation timed out. Falling back to sequential evaluation.")
        return [cost_function(candidate, max_children, penalty) for candidate in candidate_solutions]
    except Exception as e:
        logging.warning(f"ProcessPoolExecutor failed: {e}. Falling back to sequential evaluation.")
        # Fallback to sequential evaluation (CPU-only)
        return [cost_function(candidate, max_children, penalty) for candidate in candidate_solutions]

def parallel_edge_swap_evaluation(G, current_tree, edge_candidates, max_children, penalty, max_workers=None):
    """
    Evaluate multiple edge swap candidates in parallel with adaptive resource management.

    Args:
        G: Original graph
        current_tree: Current spanning tree
        edge_candidates: List of (edge_to_remove, edge_to_add) tuples
        max_children: Maximum allowed number of children
        penalty: Penalty for violations
        max_workers: Maximum number of worker processes (default: adaptive calculation)

    Returns:
        List of (cost, modified_tree) tuples for valid swaps, None for invalid swaps
    """
    if len(edge_candidates) <= 1:
        # Skip parallelization for single candidates
        if edge_candidates:
            return [_evaluate_single_edge_swap(G, current_tree, edge_candidates[0], max_children, penalty)]
        return []

    # Use adaptive resource management for worker calculation
    if max_workers is None:
        max_workers = calculate_optimal_workers(safety_margin=0.5, min_ram_per_worker=MIN_RAM_PER_WORKER)
        max_workers = min(max_workers, len(edge_candidates))  # Don't exceed number of candidates

    # ADAPTIVE SCALING: Use operation-specific limits based on system type
    max_workers = get_adaptive_max_workers_for_operation("edge_swap", max_workers)

    # Monitor CPU and adjust workers if needed (more aggressive threshold)
    max_workers = adaptive_worker_adjustment(max_workers, cpu_threshold=75.0)

    # Skip parallelization if only 1 worker is optimal or very few candidates
    if max_workers == 1 or len(edge_candidates) < 5:  # Increased threshold for parallelization
        logging.debug("Using sequential edge swap evaluation due to resource constraints or few candidates")
        return [_evaluate_single_edge_swap(G, current_tree, candidate, max_children, penalty)
                for candidate in edge_candidates]

    try:
        # Check system stability before starting intensive parallel operations
        is_stable, stability_message = check_system_stability()
        if not is_stable:
            logging.warning(f"System instability detected: {stability_message}. Reducing parallelization.")
            max_workers = 1

        # Calculate adaptive timeout based on problem size and complexity
        adaptive_timeout = min(40, max(8, len(edge_candidates) * 1.5))  # 1.5 seconds per candidate, max 40s

        logging.debug(f"Starting parallel edge swap evaluation with {max_workers} workers for {len(edge_candidates)} candidates (timeout: {adaptive_timeout}s)")

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all edge swap evaluation tasks
            futures = [
                executor.submit(_evaluate_single_edge_swap, G, current_tree.copy(), candidate, max_children, penalty)
                for candidate in edge_candidates
            ]

            # Collect results as they complete with adaptive timeout and monitoring
            results = []
            completed_count = 0
            start_time = time.time()

            for future in concurrent.futures.as_completed(futures, timeout=adaptive_timeout):
                try:
                    result = future.result(timeout=3)  # Individual task timeout
                    results.append(result)
                    completed_count += 1

                    # Monitor system resources periodically during execution
                    if completed_count % max(1, len(futures) // 3) == 0:
                        cpu_usage = monitor_cpu_usage()
                        elapsed_time = time.time() - start_time

                        if cpu_usage > 95.0:
                            logging.warning(f"Very high CPU usage detected ({cpu_usage:.1f}%) during edge swap evaluation")
                            # Consider emergency cleanup if CPU usage is critical
                            if cpu_usage > 98.0:
                                emergency_resource_cleanup()

                        # Check if we're taking too long
                        if elapsed_time > adaptive_timeout * 0.8:
                            logging.warning(f"Edge swap evaluation taking longer than expected ({elapsed_time:.1f}s)")

                except concurrent.futures.TimeoutError:
                    logging.warning(f"Individual edge swap task timed out")
                    results.append(None)
                except Exception as e:
                    logging.warning(f"Parallel edge swap evaluation failed for one candidate: {e}")
                    results.append(None)

            return results

    except concurrent.futures.TimeoutError:
        logging.warning("Parallel edge swap evaluation timed out. Falling back to sequential evaluation.")
        return [_evaluate_single_edge_swap(G, current_tree, candidate, max_children, penalty)
                for candidate in edge_candidates]
    except Exception as e:
        logging.warning(f"ProcessPoolExecutor failed: {e}. Falling back to sequential evaluation.")
        # Fallback to sequential evaluation
        return [_evaluate_single_edge_swap(G, current_tree, candidate, max_children, penalty)
                for candidate in edge_candidates]

def _evaluate_single_edge_swap(G, tree, edge_candidate, max_children, penalty):
    """
    Helper function to evaluate a single edge swap.

    Args:
        G: Original graph
        tree: Spanning tree (will be modified)
        edge_candidate: (edge_to_remove, edge_to_add) tuple
        max_children: Maximum allowed number of children
        penalty: Penalty for violations

    Returns:
        (cost, modified_tree) tuple if swap is valid, None otherwise
    """
    edge_to_remove, edge_to_add = edge_candidate

    try:
        # CRITICAL FIX: Create a deep copy to avoid modifying the original tree
        temp_tree = tree.copy()

        # Verify edge_to_remove exists in the tree before attempting removal
        if not temp_tree.has_edge(*edge_to_remove):
            logging.debug(f"Edge {edge_to_remove} not found in tree during swap evaluation")
            return None

        # Verify edge_to_add exists in the original graph
        if not G.has_edge(*edge_to_add):
            logging.debug(f"Edge {edge_to_add} not found in original graph")
            return None

        # Apply the edge swap on the copy
        temp_tree.remove_edge(*edge_to_remove)
        temp_tree.add_edge(*edge_to_add, weight=G[edge_to_add[0]][edge_to_add[1]]['weight'])

        # Verify that the new structure is still a valid tree
        if nx.is_connected(temp_tree) and nx.is_tree(temp_tree):
            cost = calculate_cost_local(temp_tree, max_children, penalty)
            return (cost, temp_tree)
        else:
            return None

    except KeyError as e:
        logging.debug(f"KeyError in edge swap evaluation: {e}")
        return None
    except Exception as e:
        logging.debug(f"Exception in edge swap evaluation: {e}")
        return None

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
    # Automatic parameter adaptation for large instances
    num_nodes = len(G.nodes)
    original_max_iterations = max_iterations
    original_neighborhood_size = 1

    if num_nodes >= 1000:
        # Increase max_iterations to handle larger search spaces
        max_iterations = max(max_iterations * 2, 10000)  # At least double, minimum 10000
        max_iterations = min(max_iterations, 20000)  # Cap at 20000 to prevent excessive computation

        # Reduce neighborhood_size to 1 to limit computational complexity
        initial_neighborhood_size = 1

        # Log warning about parameter adaptation
        warning_msg = (f"Large instance detected ({num_nodes} nodes). "
                      f"Adapting Local Search parameters: "
                      f"max_iterations: {original_max_iterations} → {max_iterations}, "
                      f"neighborhood_size: {original_neighborhood_size} → {initial_neighborhood_size}")
        logging.warning(warning_msg)

        if queue:
            queue.put(("log", (warning_msg, "warning")))
    else:
        initial_neighborhood_size = 1

    current_tree = initial_tree.copy()
    best_tree = current_tree.copy()
    best_cost = calculate_cost_local(best_tree, max_children, penalty)

    # Imposta la dimensione iniziale del quartiere
    neighborhood_size = initial_neighborhood_size
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

    # Automatic parameter adaptation for large instances
    num_nodes = len(G.nodes)
    original_max_iterations = max_iterations
    original_cooling_rate = cooling_rate
    original_min_temperature = 0.01  # Default value from the original code

    if num_nodes >= 1000:
        # Reduce max_iterations to prevent excessive computation time
        max_iterations = max(max_iterations // 2, 5000)  # At least half, minimum 5000
        max_iterations = min(max_iterations, 8000)  # Cap at 8000 for large instances

        # Set cooling_rate = 0.9 for faster cooling
        cooling_rate = 0.9

        # Increase min_temperature to avoid getting stuck in local optima
        adapted_min_temperature = 0.1  # 10x higher than default

        # Log warning about parameter adaptation
        warning_msg = (f"Large instance detected ({num_nodes} nodes). "
                      f"Adapting Simulated Annealing parameters: "
                      f"max_iterations: {original_max_iterations} → {max_iterations}, "
                      f"cooling_rate: {original_cooling_rate} → {cooling_rate}, "
                      f"min_temperature: {original_min_temperature} → {adapted_min_temperature}")
        logging.warning(warning_msg)

        if queue:
            queue.put(("log", (warning_msg, "warning")))
    else:
        adapted_min_temperature = 0.01  # Use default value

    global sa_cost_calls
    sa_cost_calls[0] += 1

    # Inizia con l'albero iniziale, se fornito, altrimenti utilizza un approccio di base
    if initial_tree is not None:
        T = initial_tree.copy()
        if queue:
            queue.put(("log", (f"Iniziando SA dall'albero fornito (ad esempio: da Local Search o Greedy)", "info")))
    else:
        # Costruisci sempre la soluzione iniziale con la Greedy
        T, _ = greedy_spanning_tree(G, max_children=max_children, penalty=penalty)
        if queue:
            queue.put(("log", (f"Iniziando SA da una soluzione Greedy", "info")))

    # Calcola le chimate alla funzione di costo iniziale
    cost = calculate_cost_sa(T, max_children, penalty)
    sa_cost_calls[0] += 1
    best_cost = cost
    best_tree = T.copy()

    # Parametri di ricottura simulata migliorati
    temperature = initial_temperature
    min_temperature = adapted_min_temperature  # Use adapted value for large instances
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
        # Use adaptive parallel neighbor generation for large graphs and high temperatures
        if num_nodes > 100 and temperature > initial_temperature * 0.5 and iteration % 10 == 0:
            # Generate multiple neighbors in parallel and select the best one
            try:
                # Use adaptive resource management for neighbor generation
                optimal_workers = calculate_optimal_workers(safety_margin=0.8, min_ram_per_worker=0.2)
                num_neighbors = min(optimal_workers, 4, num_nodes // 50)  # Adaptive neighbor count

                # Monitor CPU and adjust if needed
                current_cpu = monitor_cpu_usage()
                if current_cpu > 85.0:
                    num_neighbors = max(1, num_neighbors // 2)  # Reduce neighbors if CPU is high
                    logging.debug(f"Reducing neighbor candidates to {num_neighbors} due to high CPU usage ({current_cpu:.1f}%)")

                neighbor_candidates = []

                for _ in range(num_neighbors):
                    candidate = T.copy()
                    strategy_prob = temperature / initial_temperature

                    if random.random() < strategy_prob:
                        generate_neighbor_tree(G, candidate, max_children, penalty)
                    else:
                        _generate_targeted_neighbor(G, candidate, max_children, penalty)

                    neighbor_candidates.append(candidate)

                # Evaluate all candidates in parallel (GPU acceleration removed for stability)
                costs = parallel_cost_evaluation(neighbor_candidates, max_children, penalty, calculate_cost_sa)

                # Select the best neighbor
                best_idx = min(range(len(costs)), key=lambda i: costs[i])
                neighbor_tree = neighbor_candidates[best_idx]
                neighbor_cost = costs[best_idx]

                sa_cost_calls[0] += len(neighbor_candidates)  # Update counter for all evaluations

            except Exception as e:
                logging.warning(f"Parallel neighbor generation failed, falling back to sequential: {e}")
                # Fallback to sequential neighbor generation
                neighbor_tree = T.copy()
                strategy_prob = temperature / initial_temperature

                if random.random() < strategy_prob:
                    generate_neighbor_tree(G, neighbor_tree, max_children, penalty)
                else:
                    _generate_targeted_neighbor(G, neighbor_tree, max_children, penalty)

                neighbor_cost = calculate_cost_sa(neighbor_tree, max_children, penalty)
                sa_cost_calls[0] += 1
        else:
            # Sequential neighbor generation (default)
            neighbor_tree = T.copy()
            strategy_prob = temperature / initial_temperature

            if random.random() < strategy_prob:
                generate_neighbor_tree(G, neighbor_tree, max_children, penalty)
            else:
                _generate_targeted_neighbor(G, neighbor_tree, max_children, penalty)

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
    # CRITICAL FIX: Ensure tree has edges before attempting to remove one
    if len(tree.edges()) == 0:
        logging.warning("Tree has no edges, cannot generate neighbor")
        return tree

    # Choose a random edge to remove
    edge_to_remove = random.choice(list(tree.edges()))
    u, v = edge_to_remove

    # CRITICAL FIX: Verify edge exists before removal
    if not tree.has_edge(u, v):
        logging.debug(f"Edge {edge_to_remove} not found in tree during neighbor generation")
        return tree

    try:
        # Remove the edge
        tree.remove_edge(u, v)

        # Find the two components
        components = list(nx.connected_components(tree))

        if len(components) == 1:
            # The removal didn't disconnect the tree, add the edge back and try again
            if G.has_edge(u, v):
                tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
            return generate_neighbor_tree(G, tree, max_children, penalty)

        # Find a new edge to connect the components
        component1 = components[0]
        component2 = components[1]
    except (KeyError, nx.NetworkXError) as e:
        logging.debug(f"Error during neighbor generation: {e}")
        # Try to restore the original edge if possible
        if G.has_edge(u, v):
            tree.add_edge(u, v, weight=G.edges[u, v]['weight'])
        return tree

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
    Implementa una strategia best-improvement per il local search con parallelizzazione.
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

    # Generate candidate edge swaps
    edge_candidates = []
    for _ in range(neighborhood_size):
        edge_to_remove = random.choice(tree_edges)
        edge_to_add = random.choice(non_tree_edges)
        edge_candidates.append((edge_to_remove, edge_to_add))

    # Use adaptive parallel evaluation for multiple candidates
    if neighborhood_size > 1 and len(G.nodes) > 30:  # Lower threshold for parallelization
        # Parallel evaluation with adaptive resource management
        try:
            results = parallel_edge_swap_evaluation(G, current_tree, edge_candidates, max_children, penalty)

            # Find the best valid result
            best_result = None
            best_swap_info = None

            for i, result in enumerate(results):
                if result is not None:
                    cost, modified_tree = result
                    if cost < best_cost:
                        best_cost = cost
                        best_result = modified_tree
                        best_swap_info = (edge_candidates[i][0], edge_candidates[i][1], cost)

            # Apply the best improvement if found
            if best_result is not None:
                current_tree.clear()
                current_tree.add_edges_from(best_result.edges(data=True))

                if best_swap_info:
                    logging.debug(f"Adaptive parallel best improvement swap applied: removed {best_swap_info[0]}, "
                                 f"added {best_swap_info[1]}, new cost: {best_swap_info[2]}")
                return True

        except Exception as e:
            logging.warning(f"Adaptive parallel edge swap failed, falling back to sequential: {e}")

    # Sequential evaluation (fallback or for small neighborhood_size)
    best_tree = None
    best_swap_info = None

    for edge_to_remove, edge_to_add in edge_candidates:
        # CRITICAL FIX: Verify edges exist before attempting swap
        if not current_tree.has_edge(*edge_to_remove):
            logging.debug(f"Edge {edge_to_remove} not found in current tree, skipping swap")
            continue

        if not G.has_edge(*edge_to_add):
            logging.debug(f"Edge {edge_to_add} not found in original graph, skipping swap")
            continue

        # Crea copia temporanea dell'albero e applica lo scambio
        temp_tree = current_tree.copy()

        try:
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
        except (KeyError, nx.NetworkXError) as e:
            logging.debug(f"Error during edge swap {edge_to_remove} -> {edge_to_add}: {e}")
            continue

    # Se abbiamo trovato almeno un miglioramento, applica il migliore
    if best_tree is not None:
        current_tree.clear()
        current_tree.add_edges_from(best_tree.edges(data=True))

        # Log opzionale per debug
        if best_swap_info:
            logging.debug(f"Sequential best improvement swap applied: removed {best_swap_info[0]}, "
                         f"added {best_swap_info[1]}, new cost: {best_swap_info[2]}")

        return True

    return False  # nessun miglioramento trovato

def fix_constraint_violations(G, current_tree, constrained_nodes, max_children, penalty, neighborhood_size=1):
    """
    Corregge i vincoli violati provando più alternative per ciascun nodo con parallelizzazione.
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

    # Use adaptive parallel evaluation for multiple constrained nodes when beneficial
    if len(constrained_nodes) > 1 and neighborhood_size > 1 and len(G.nodes) > 30:  # Lower threshold
        try:
            # Generate all repair candidates for all constrained nodes
            all_candidates = []
            node_candidate_mapping = {}

            for node in constrained_nodes:
                node_candidates = _generate_constraint_repair_candidates(
                    G, current_tree, node, neighborhood_size
                )
                if node_candidates:
                    start_idx = len(all_candidates)
                    all_candidates.extend(node_candidates)
                    end_idx = len(all_candidates)
                    node_candidate_mapping[node] = (start_idx, end_idx)

            if all_candidates:
                # Adaptive parallel evaluation of all candidates
                results = parallel_edge_swap_evaluation(G, current_tree, all_candidates, max_children, penalty)

                # Find the best improvement across all nodes
                best_result = None
                best_node = None

                for node, (start_idx, end_idx) in node_candidate_mapping.items():
                    node_results = results[start_idx:end_idx]

                    for result in node_results:
                        if result is not None:
                            cost, modified_tree = result
                            if cost < best_cost:
                                best_cost = cost
                                best_result = modified_tree
                                best_node = node

                # Apply the best improvement if found
                if best_result is not None:
                    current_tree.clear()
                    current_tree.add_edges_from(best_result.edges(data=True))
                    modified = True
                    logging.debug(f"Adaptive parallel constraint violation fixed for node {best_node}, new cost: {best_cost}")
                    return modified

        except Exception as e:
            logging.warning(f"Adaptive parallel constraint fixing failed, falling back to sequential: {e}")

    # Sequential processing (fallback or for small problems)
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

            # CRITICAL FIX: Verify edges exist before attempting swap
            if not current_tree.has_edge(node, neighbor_to_remove):
                logging.debug(f"Edge ({node}, {neighbor_to_remove}) not found in tree, skipping")
                continue

            if not G.has_edge(node, neighbor_to_add):
                logging.debug(f"Edge ({node}, {neighbor_to_add}) not found in original graph, skipping")
                continue

            # Crea copia temporanea e applica lo scambio
            temp_tree = current_tree.copy()

            try:
                temp_tree.remove_edge(node, neighbor_to_remove)
                temp_tree.add_edge(node, neighbor_to_add, weight=G[node][neighbor_to_add]['weight'])

                # Verifica che la nuova struttura sia ancora un albero valido e connesso
                if nx.is_connected(temp_tree) and nx.is_tree(temp_tree):
                    new_cost = calculate_cost_local(temp_tree, max_children, penalty)

                    # Se questo tentativo è migliore del migliore per questo nodo
                    if new_cost < best_cost_for_node:
                        best_cost_for_node = new_cost
                        best_tree_for_node = temp_tree.copy()
            except (KeyError, nx.NetworkXError) as e:
                logging.debug(f"Error during constraint violation fix for node {node}: {e}")
                continue

        # Se abbiamo trovato un miglioramento per questo nodo, applicalo
        if best_tree_for_node is not None:
            current_tree.clear()
            current_tree.add_edges_from(best_tree_for_node.edges(data=True))
            best_cost = best_cost_for_node
            modified = True

            # Log opzionale per debug
            logging.debug(f"Sequential constraint violation fixed for node {node}, new cost: {best_cost}")

    return modified

def _generate_constraint_repair_candidates(G, current_tree, node, neighborhood_size):
    """
    Generate edge swap candidates for repairing constraint violations for a specific node.

    Args:
        G: Original graph
        current_tree: Current spanning tree
        node: Node with constraint violations
        neighborhood_size: Number of repair attempts to generate

    Returns:
        List of (edge_to_remove, edge_to_add) tuples
    """
    candidates = []

    # Get edges from the violating node
    tree_edges_node = [(neighbor, current_tree.edges[node, neighbor]['weight'])
                      for neighbor in current_tree.neighbors(node)]

    # Find potential edges from the original graph that are not in the tree
    non_tree_edges_node = []
    for neighbor in G.neighbors(node):
        if not current_tree.has_edge(node, neighbor):
            weight = G.edges[node, neighbor]['weight']
            non_tree_edges_node.append((neighbor, weight))

    if not tree_edges_node or not non_tree_edges_node:
        return candidates

    # Generate neighborhood_size candidates
    for _ in range(neighborhood_size):
        # Select edge to remove (preferring high weight edges)
        tree_edges_node.sort(key=lambda x: -x[1])
        if len(tree_edges_node) > 1:
            idx = min(int(random.expovariate(2) * len(tree_edges_node)), len(tree_edges_node) - 1)
            neighbor_to_remove, _ = tree_edges_node[idx]
        else:
            neighbor_to_remove, _ = tree_edges_node[0]

        # Select edge to add (preferring low weight edges)
        non_tree_edges_node.sort(key=lambda x: x[1])
        if len(non_tree_edges_node) > 1:
            idx = min(int(random.expovariate(2) * len(non_tree_edges_node)), len(non_tree_edges_node) - 1)
            neighbor_to_add, _ = non_tree_edges_node[idx]
        else:
            neighbor_to_add, _ = non_tree_edges_node[0]

        edge_to_remove = (node, neighbor_to_remove)
        edge_to_add = (node, neighbor_to_add)
        candidates.append((edge_to_remove, edge_to_add))

    return candidates

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
    Test different spanning tree algorithms on a graph instance with adaptive resource management.

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
    # Initialize adaptive resource management and log system capabilities
    if queue:
        queue.put(("log", (f"Initializing adaptive resource management for {instance_name}...", "info")))

    # Detect and log system resources
    cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()
    optimal_workers = calculate_optimal_workers(safety_margin=0.7)

    if queue:
        queue.put(("log", (f"System resources: {cpu_cores} CPU cores, {total_ram_gb:.1f}GB RAM ({available_ram_gb:.1f}GB available)", "info")))
        queue.put(("log", (f"Optimal worker count: {optimal_workers} (with 70% safety margin)", "info")))



    # Optimize memory representation for large graphs
    if len(G.nodes()) > 100:  # Solo per grafi di dimensioni significative
        if queue:
            queue.put(("log", (f"Ottimizzando rappresentazione del grafo per {instance_name}...", "info")))
        G_opt, node_mapping, _ = optimize_memory_usage(G.copy())
        G = G_opt  # Usa il grafo ottimizzato
        results = {"graph": G, "node_mapping": node_mapping}
    else:
        G = G.copy()
        results = {"graph": G}

    # Store resource management info in results
    results["system_resources"] = {
        "cpu_cores": cpu_cores,
        "total_ram_gb": total_ram_gb,
        "available_ram_gb": available_ram_gb,
        "optimal_workers": optimal_workers
    }

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

    # 🔬 PRECISION IMPROVEMENT: Enhanced memory tracking with memory_profiler
    def get_memory_usage_precise():
        """
        Get precise memory usage using memory_profiler for more accurate measurements.
        Falls back to psutil if memory_profiler is not available.

        Returns:
            float: Memory usage in KB
        """
        gc.collect()  # Force garbage collection for accurate measurement

        if MEMORY_PROFILER_AVAILABLE:
            try:
                # Use memory_profiler for precise measurement
                current_memory = memory_usage()[0]  # Returns memory in MB
                return current_memory * 1024  # Convert to KB for consistency
            except Exception as e:
                logging.warning(f"memory_profiler measurement failed: {e}, falling back to psutil")

        # Fallback to psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / 1024  # in KB



    def measure_algorithm_memory(algorithm_func, *args, **kwargs):
        """
        Measure memory usage during algorithm execution using memory_profiler.

        Args:
            algorithm_func: The algorithm function to execute
            *args: Arguments for the algorithm function
            **kwargs: Keyword arguments for the algorithm function

        Returns:
            tuple: (result, peak_memory_kb, average_memory_kb)
        """
        if MEMORY_PROFILER_AVAILABLE:
            try:
                # Wrapper function for memory_usage monitoring
                def algorithm_wrapper():
                    return algorithm_func(*args, **kwargs)

                # Monitor memory usage during execution
                mem_usage = memory_usage((algorithm_wrapper, ()), interval=0.1, timeout=None)

                if mem_usage:
                    peak_memory_mb = max(mem_usage)
                    avg_memory_mb = sum(mem_usage) / len(mem_usage)

                    # Convert to KB for consistency
                    peak_memory_kb = peak_memory_mb * 1024
                    avg_memory_kb = avg_memory_mb * 1024

                    # Execute the function to get the result
                    result = algorithm_func(*args, **kwargs)

                    return result, peak_memory_kb, avg_memory_kb
                else:
                    # Fallback if memory monitoring failed
                    result = algorithm_func(*args, **kwargs)
                    current_memory = get_memory_usage_precise()
                    return result, current_memory, current_memory

            except Exception as e:
                logging.warning(f"memory_profiler monitoring failed: {e}, using fallback measurement")

        # Fallback to simple before/after measurement
        start_memory = get_memory_usage_precise()
        result = algorithm_func(*args, **kwargs)
        end_memory = get_memory_usage_precise()

        memory_used = max(0, end_memory - start_memory)
        return result, memory_used, memory_used

    # 1. Run Greedy Algorithm
    if check_stop():
        return results

    update_progress("Greedy Spanning Tree", 0, "greedy")
    if queue:
        queue.put(("log", (f"🔬 Esecuzione algoritmo greedy con misurazione memoria precisa per {instance_name}...", "info")))

    start_time = time.time()

    # 🔬 PRECISION IMPROVEMENT: Use memory_profiler for precise memory measurement
    def greedy_algorithm_wrapper():
        # Execute greedy algorithm with safety wrapper and adaptive timeout
        graph_size = len(G.nodes())
        greedy_timeout = adaptive_timeout_calculation(graph_size, base_timeout=60)  # Base 1 minute for greedy

        try:
            return safe_execution_wrapper(
                greedy_spanning_tree,
                G, max_children, penalty,
                timeout=greedy_timeout
            )
        except TimeoutError:
            if queue:
                queue.put(("log", (f"Greedy algorithm timed out after {greedy_timeout}s. Using fallback solution.", "warning")))
            # Fallback to a simple MST-based solution
            greedy_tree = nx.minimum_spanning_tree(G)
            greedy_cost = calculate_cost_greedy(greedy_tree, max_children, penalty)
            return greedy_tree, greedy_cost
        except Exception as e:
            if queue:
                queue.put(("log", (f"Greedy algorithm failed: {e}. Using fallback solution.", "error")))
            # Emergency fallback
            greedy_tree = nx.Graph()
            greedy_tree.add_nodes_from(G.nodes())
            greedy_cost = float('inf')
            return greedy_tree, greedy_cost

    # Measure memory usage during algorithm execution
    try:
        (greedy_tree, greedy_cost), peak_memory, avg_memory = measure_algorithm_memory(greedy_algorithm_wrapper)
    except Exception as e:
        logging.error(f"Memory profiling failed for greedy algorithm: {e}")
        # Fallback to traditional measurement
        greedy_tree, greedy_cost = greedy_algorithm_wrapper()
        peak_memory = avg_memory = get_memory_usage_precise()

    end_time = time.time()
    greedy_time = end_time - start_time

    # 🔬 PRECISION IMPROVEMENT: Use precise memory measurements
    greedy_memory = peak_memory  # Use peak memory as the primary metric

    if queue:
        queue.put(("log", (f"📊 Greedy - Memoria peak: {peak_memory:.1f}KB, avg: {avg_memory:.1f}KB", "info")))

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
        queue.put(("log", (f"🔬 Esecuzione ricerca locale con misurazione memoria precisa per {instance_name}...", "info")))

    start_time = time.time()
    graph_size = len(G.nodes())  # Define graph_size for local search

    # 🔬 PRECISION IMPROVEMENT: Use memory_profiler for precise memory measurement
    def local_search_wrapper():
        # Execute Local Search with safety wrapper and adaptive timeout
        local_timeout = adaptive_timeout_calculation(graph_size, base_timeout=300)  # Base 5 minutes for local search

        try:
            # Use parallel version for graphs larger than a threshold
            if len(G.nodes()) > 50:
                # Check system stability before parallel execution
                is_stable, stability_message = check_system_stability()
                if is_stable:
                    num_threads = min(8, os.cpu_count() or 4)  # Limita a 8 thread o meno
                    local_tree, local_calls, local_score_history = safe_execution_wrapper(
                        parallel_local_search,
                        G, greedy_tree, max_children, penalty,
                        num_threads=num_threads,
                        timeout=local_timeout
                    )
                    if queue:
                        queue.put(("log", (f"Utilizzati {num_threads} thread per la ricerca locale", "info")))
                else:
                    if queue:
                        queue.put(("log", (f"System instability detected: {stability_message}. Using sequential local search.", "warning")))
                    local_tree, local_calls, local_score_history = safe_execution_wrapper(
                        adaptive_neighborhood_local_search,
                        G, greedy_tree, max_children, penalty,
                        timeout=local_timeout
                    )
            else:
                local_tree, local_calls, local_score_history = safe_execution_wrapper(
                    adaptive_neighborhood_local_search,
                    G, greedy_tree, max_children, penalty,
                    timeout=local_timeout
                )
            return local_tree, local_calls, local_score_history
        except TimeoutError:
            if queue:
                queue.put(("log", (f"Local Search timed out after {local_timeout}s. Using greedy solution.", "warning")))
            # Fallback to greedy solution
            return greedy_tree.copy(), 0, []
        except Exception as e:
            if queue:
                queue.put(("log", (f"Local Search failed: {e}. Using greedy solution.", "error")))
            # Emergency fallback
            emergency_resource_cleanup()
            return greedy_tree.copy(), 0, []

    # Measure memory usage during algorithm execution
    try:
        (local_tree, local_calls, local_score_history), peak_memory, avg_memory = measure_algorithm_memory(local_search_wrapper)
        local_search_cost_calls[0] = local_calls  # Update the global counter
    except Exception as e:
        logging.error(f"Memory profiling failed for local search: {e}")
        # Fallback to traditional measurement
        local_tree, local_calls, local_score_history = local_search_wrapper()
        local_search_cost_calls[0] = local_calls
        peak_memory = avg_memory = get_memory_usage_precise()

    end_time = time.time()
    local_cost = calculate_cost_local(local_tree, max_children, penalty)
    local_time = end_time - start_time

    # 🔬 PRECISION IMPROVEMENT: Use precise memory measurements
    local_memory = peak_memory  # Use peak memory as the primary metric

    if queue:
        queue.put(("log", (f"📊 Local Search - Memoria peak: {peak_memory:.1f}KB, avg: {avg_memory:.1f}KB", "info")))

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
        queue.put(("log", (f"🔬 Esecuzione simulated annealing con misurazione memoria precisa per {instance_name}...", "info")))
        queue.put(("log", (f"Utilizzo dell'albero ottimizzato da Local Search come soluzione iniziale", "info")))

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

    # 🔬 PRECISION IMPROVEMENT: Use memory_profiler for precise memory measurement
    def sa_wrapper():
        # Execute Simulated Annealing with safety wrapper and adaptive timeout
        sa_timeout = adaptive_timeout_calculation(graph_size, base_timeout=600)  # Base 10 minutes for SA

        try:
            # Check system stability before SA execution
            is_stable, stability_message = check_system_stability()
            if not is_stable:
                if queue:
                    queue.put(("log", (f"System instability detected: {stability_message}. SA may run with reduced performance.", "warning")))

            # Utilizza local_tree invece di greedy_tree come soluzione iniziale per SA
            sa_tree, sa_cost, sa_iterations, sa_accepts, sa_score_history = safe_execution_wrapper(
                simulated_annealing_spanning_tree,
                G, max_children, penalty,
                initial_tree=local_tree,  # Usa l'albero ottimizzato dalla ricerca locale
                stop_event=stop_event,
                queue=queue,
                progress_callback=sa_progress_callback,
                timeout=sa_timeout
            )
            return sa_tree, sa_cost, sa_iterations, sa_accepts, sa_score_history
        except TimeoutError:
            if queue:
                queue.put(("log", (f"Simulated Annealing timed out after {sa_timeout}s. Using local search solution.", "warning")))
            # Fallback to local search solution
            sa_tree = local_tree.copy()
            sa_cost = calculate_cost_sa(sa_tree, max_children, penalty)
            return sa_tree, sa_cost, 0, 0, []
        except Exception as e:
            if queue:
                queue.put(("log", (f"Simulated Annealing failed: {e}. Using local search solution.", "error")))
            # Emergency fallback
            emergency_resource_cleanup()
            sa_tree = local_tree.copy()
            sa_cost = calculate_cost_sa(sa_tree, max_children, penalty)
            return sa_tree, sa_cost, 0, 0, []

    # Measure memory usage during algorithm execution
    try:
        (sa_tree, sa_cost, sa_iterations, sa_accepts, sa_score_history), peak_memory, avg_memory = measure_algorithm_memory(sa_wrapper)
    except Exception as e:
        logging.error(f"Memory profiling failed for simulated annealing: {e}")
        # Fallback to traditional measurement
        sa_tree, sa_cost, sa_iterations, sa_accepts, sa_score_history = sa_wrapper()
        peak_memory = avg_memory = get_memory_usage_precise()

    end_time = time.time()
    sa_cost = calculate_cost_sa(sa_tree, max_children, penalty)
    sa_time = end_time - start_time

    # 🔬 PRECISION IMPROVEMENT: Use precise memory measurements
    sa_memory = peak_memory  # Use peak memory as the primary metric

    if queue:
        queue.put(("log", (f"📊 Simulated Annealing - Memoria peak: {peak_memory:.1f}KB, avg: {avg_memory:.1f}KB", "info")))

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

def _parallel_local_search_worker(args):
    """
    Worker function for parallel local search that can be pickled.
    """
    G, initial_tree, max_degree, penalty, seed = args

    # Set different random seed for each process to ensure diversity
    random.seed(seed)
    np.random.seed(seed)

    return adaptive_neighborhood_local_search(G, initial_tree.copy(), max_degree, penalty, stop_event=None, queue=None)

def parallel_local_search(G, initial_tree, max_degree, penalty, num_threads=None, stop_event=None, queue=None):
    """
    Enhanced parallel version of the local search algorithm using adaptive resource management.
    CRITICAL: Hard-limited to prevent system crashes.
    """
    # CRITICAL: Force single worker for large graphs to prevent crashes
    graph_size = len(G.nodes())
    if graph_size > 500:
        if queue:
            queue.put(("log", (f"Large graph detected ({graph_size} nodes). Forcing sequential execution to prevent crashes.", "warning")))
        return adaptive_neighborhood_local_search(G, initial_tree, max_degree, penalty, stop_event=stop_event, queue=queue)

    # Use adaptive resource management for worker calculation (very conservative)
    if num_threads is None:
        max_workers = calculate_optimal_workers(safety_margin=0.4, min_ram_per_worker=1.0)
    else:
        max_workers = min(num_threads, calculate_optimal_workers(safety_margin=0.4, min_ram_per_worker=1.0))

    # CRITICAL: Hard limit to 2 workers maximum
    max_workers = min(max_workers, 2)

    # Monitor CPU and adjust workers if needed (very aggressive threshold)
    max_workers = adaptive_worker_adjustment(max_workers, cpu_threshold=70.0)

    # Force sequential if system is not stable
    is_stable, stability_message = check_system_stability()
    if not is_stable:
        if queue:
            queue.put(("log", (f"System instability detected: {stability_message}. Using sequential local search.", "warning")))
        return adaptive_neighborhood_local_search(G, initial_tree, max_degree, penalty, stop_event=stop_event, queue=queue)

    # Log resource usage information
    if queue:
        queue.put(("log", (f"Parallel Local Search using {max_workers} workers (SAFE MODE - max 2)", "info")))

    logging.info(f"Starting parallel local search with {max_workers} workers (SAFE MODE)")

    results = []

    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Prepare arguments for worker processes
            seeds = [random.randint(0, 1000000) for _ in range(max_workers)]
            worker_args = [(G, initial_tree, max_degree, penalty, seed) for seed in seeds]

            # Submit tasks
            futures = [executor.submit(_parallel_local_search_worker, args) for args in worker_args]

            # Collect results as they complete with monitoring
            total_calls = 0
            best_score_history = []

            for future in concurrent.futures.as_completed(futures):
                if stop_event and stop_event.is_set():
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break

                try:
                    tree, calls, score_history = future.result()
                    results.append((tree, calls, score_history))
                    total_calls += calls
                    if len(score_history) > len(best_score_history):
                        best_score_history = score_history

                    # Log progress if queue is available
                    if queue:
                        queue.put(("log", (f"Parallel local search process completed: {calls} cost calls", "info")))

                except Exception as e:
                    logging.warning(f"Parallel local search task failed: {e}")

        # Find the best result among all processes
        if results:
            best_result = min(results, key=lambda x: calculate_cost_local(x[0], max_degree, penalty))

            if queue:
                queue.put(("log", (f"Parallel local search completed: {len(results)} processes, best cost: {calculate_cost_local(best_result[0], max_degree, penalty)}", "success")))

            return best_result[0], total_calls, best_result[2]
        else:
            # No results obtained, fallback to sequential
            if queue:
                queue.put(("log", ("Parallel local search failed, falling back to sequential", "warning")))
            return adaptive_neighborhood_local_search(G, initial_tree, max_degree, penalty, stop_event=stop_event, queue=queue)

    except Exception as e:
        logging.warning(f"ProcessPoolExecutor failed in parallel_local_search: {e}. Falling back to sequential.")
        # Fallback to sequential execution
        if queue:
            queue.put(("log", ("Falling back to sequential local search", "warning")))
        return adaptive_neighborhood_local_search(G, initial_tree, max_degree, penalty, stop_event=stop_event, queue=queue)

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
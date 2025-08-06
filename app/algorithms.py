# app/algorithms.py - Main algorithms for the DCST application

#==============================================================================
#                           1. IMPORTS
#==============================================================================

# Standard library imports
import gc
import os
import sys
import math
import time
import heapq
import random
import logging
import threading
import traceback
import warnings
from typing import Dict, Any, Optional, Tuple, List
from threading import Lock, RLock, Event
from collections import defaultdict
from contextlib import contextmanager

# Third-party imports
import psutil
import numpy as np
import networkx as nx
import concurrent.futures
import multiprocessing
from functools import partial

# Local imports for configuration and performance tracking
from .performance_tracker import get_performance_tracker
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

# FIXED: Enhanced memory profiling with safe import handling
try:
    from memory_profiler import memory_usage
    MEMORY_PROFILER_AVAILABLE = True
    logging.info("memory_profiler available for precise memory measurement")

    # Test memory_profiler functionality
    def _test_memory_profiler():
        """Test if memory_profiler is working correctly."""
        try:
            # Simple test function
            def test_func():
                return [1, 2, 3]

            # Try to measure memory usage
            mem_usage = memory_usage((test_func, ()))
            return len(mem_usage) > 0
        except Exception:
            return False

    # Verify memory_profiler is actually working
    if not _test_memory_profiler():
        MEMORY_PROFILER_AVAILABLE = False
        logging.warning("memory_profiler installed but not functioning correctly, falling back to psutil")

except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    logging.warning("memory_profiler not available, falling back to psutil for memory measurement")
except Exception as e:
    MEMORY_PROFILER_AVAILABLE = False
    logging.warning(f"memory_profiler import failed with error: {e}, falling back to psutil")

# All operations use CPU-only optimizations for maximum stability

#==============================================================================
#                           2. DEPENDENCY VERIFICATION SYSTEM
#==============================================================================

class DependencyVerificationError(Exception):
    """Custom exception for dependency verification failures."""
    pass

class DependencyVerifier:
    """
    Comprehensive dependency verification system that validates all required libraries
    are available and compatible at startup.
    """

    def __init__(self):
        self.verification_results = {}
        self.critical_dependencies = {
            'numpy': {'min_version': '1.19.0', 'required': True},
            'scipy': {'min_version': '1.5.0', 'required': False},
            'networkx': {'min_version': '2.5', 'required': True},
            'psutil': {'min_version': '5.7.0', 'required': True},
            'memory_profiler': {'min_version': '0.57.0', 'required': False}
        }

    def verify_all_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Verify all dependencies and return status with detailed messages.

        Returns:
            Tuple[bool, List[str]]: (success, error_messages)
        """
        errors = []
        all_good = True

        for dep_name, dep_info in self.critical_dependencies.items():
            try:
                success, message = self._verify_single_dependency(dep_name, dep_info)
                self.verification_results[dep_name] = {'success': success, 'message': message}

                if not success:
                    if dep_info['required']:
                        all_good = False
                        errors.append(f"CRITICAL: {message}")
                    else:
                        errors.append(f"WARNING: {message}")

            except Exception as e:
                error_msg = f"Failed to verify {dep_name}: {str(e)}"
                self.verification_results[dep_name] = {'success': False, 'message': error_msg}
                if dep_info['required']:
                    all_good = False
                    errors.append(f"CRITICAL: {error_msg}")
                else:
                    errors.append(f"WARNING: {error_msg}")

        # Additional system checks
        system_checks = self._verify_system_requirements()
        if not system_checks[0]:
            errors.extend(system_checks[1])
            all_good = False

        return all_good, errors

    def _verify_single_dependency(self, dep_name: str, dep_info: Dict) -> Tuple[bool, str]:
        """Verify a single dependency."""
        try:
            if dep_name == 'numpy':
                import numpy as np
                version = np.__version__
                if self._version_compare(version, dep_info['min_version']) >= 0:
                    return True, f"NumPy {version} - OK"
                else:
                    return False, f"NumPy {version} is too old (minimum: {dep_info['min_version']})"

            elif dep_name == 'scipy':
                import scipy
                version = scipy.__version__
                if self._version_compare(version, dep_info['min_version']) >= 0:
                    return True, f"SciPy {version} - OK"
                else:
                    return False, f"SciPy {version} is too old (minimum: {dep_info['min_version']})"

            elif dep_name == 'networkx':
                import networkx as nx
                version = nx.__version__
                if self._version_compare(version, dep_info['min_version']) >= 0:
                    return True, f"NetworkX {version} - OK"
                else:
                    return False, f"NetworkX {version} is too old (minimum: {dep_info['min_version']})"

            elif dep_name == 'psutil':
                import psutil
                version = psutil.__version__
                if self._version_compare(version, dep_info['min_version']) >= 0:
                    return True, f"psutil {version} - OK"
                else:
                    return False, f"psutil {version} is too old (minimum: {dep_info['min_version']})"

            elif dep_name == 'memory_profiler':
                try:
                    import memory_profiler
                    version = getattr(memory_profiler, '__version__', 'unknown')
                    return True, f"memory_profiler {version} - OK (optional)"
                except ImportError:
                    return False, "memory_profiler not available (optional - will use psutil fallback)"

        except ImportError:
            return False, f"{dep_name} is not installed"
        except Exception as e:
            return False, f"{dep_name} verification failed: {str(e)}"

        return False, f"Unknown dependency: {dep_name}"

    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1
            return 0
        except:
            return 0  # If comparison fails, assume equal

    def _verify_system_requirements(self) -> Tuple[bool, List[str]]:
        """Verify system requirements."""
        errors = []

        try:
            # Check Python version
            if sys.version_info < (3, 7):
                errors.append("Python 3.7 or higher is required")

            # Check available memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            if available_gb < 1.0:
                errors.append(f"Very low available memory: {available_gb:.1f}GB (minimum recommended: 2GB)")
            elif available_gb < 2.0:
                errors.append(f"Low available memory: {available_gb:.1f}GB (recommended: 4GB+)")

            # Check CPU cores
            cpu_cores = psutil.cpu_count(logical=True)
            if cpu_cores < 2:
                errors.append(f"Very few CPU cores: {cpu_cores} (minimum recommended: 2)")

        except Exception as e:
            errors.append(f"System requirements check failed: {str(e)}")

        return len(errors) == 0, errors

    def get_verification_summary(self) -> str:
        """Get a formatted summary of verification results."""
        summary = ["=== Dependency Verification Summary ==="]

        for dep_name, result in self.verification_results.items():
            status = "✓" if result['success'] else "✗"
            summary.append(f"{status} {dep_name}: {result['message']}")

        return "\n".join(summary)

# Global dependency verifier instance
_dependency_verifier = None

def verify_dependencies_at_startup() -> bool:
    """
    Verify all dependencies at application startup.

    Returns:
        bool: True if all critical dependencies are satisfied

    Raises:
        DependencyVerificationError: If critical dependencies are missing
    """
    global _dependency_verifier

    if _dependency_verifier is None:
        _dependency_verifier = DependencyVerifier()

    success, errors = _dependency_verifier.verify_all_dependencies()

    # Log verification results
    summary = _dependency_verifier.get_verification_summary()
    logging.info(f"Dependency verification completed:\n{summary}")

    if errors:
        for error in errors:
            if error.startswith("CRITICAL"):
                logging.error(error)
            else:
                logging.warning(error)

    if not success:
        critical_errors = [e for e in errors if e.startswith("CRITICAL")]
        if critical_errors:
            error_msg = "Critical dependencies missing or incompatible:\n" + "\n".join(critical_errors)
            error_msg += "\n\nSuggested fixes:"
            error_msg += "\n- pip install --upgrade numpy scipy networkx psutil"
            error_msg += "\n- pip install memory_profiler (optional)"
            raise DependencyVerificationError(error_msg)

    return success

#==============================================================================
#                           3. GLOBAL VARIABLE DEFINITIONS
#==============================================================================
greedy_cost_calls = [0]
local_search_cost_calls = [0]
sa_cost_calls = [0]

# Global resource management variables with thread safety
_last_cpu_check = 0
_cpu_check_interval = 3.0  # OPTIMIZATION: Increased from CPU_CHECK_INTERVAL to reduce monitoring overhead
_current_worker_count = None
_resource_safety_margin = DEFAULT_SAFETY_MARGIN

#==============================================================================
#                           4. THREAD SAFETY ENHANCEMENTS
#==============================================================================

class ThreadSafeCounter:
    """Thread-safe counter for algorithm call tracking."""

    def __init__(self, initial_value=0):
        self._value = initial_value
        self._lock = Lock()

    def increment(self):
        with self._lock:
            self._value += 1
            return self._value

    def get(self):
        with self._lock:
            return self._value

    def reset(self):
        with self._lock:
            self._value = 0

class ThreadSafeResourceManager:
    """
    Thread-safe resource manager for parallel operations.
    Manages shared resources and ensures atomic operations.
    """

    def __init__(self):
        self._resource_lock = RLock()  # Reentrant lock for nested calls
        self._worker_count_lock = Lock()
        self._memory_stats_lock = Lock()
        self._performance_data_lock = Lock()

        # Thread-safe data structures
        self._active_operations = defaultdict(int)
        self._resource_usage_history = []
        self._performance_metrics = {}

        # Resource monitoring
        self._last_cpu_check = 0
        self._last_memory_check = 0
        self._check_interval = 1.0

    @contextmanager
    def resource_operation(self, operation_type: str):
        """Context manager for thread-safe resource operations."""
        with self._resource_lock:
            self._active_operations[operation_type] += 1
            operation_id = f"{operation_type}_{threading.current_thread().ident}_{time.time()}"

        try:
            yield operation_id
        finally:
            with self._resource_lock:
                self._active_operations[operation_type] -= 1
                if self._active_operations[operation_type] <= 0:
                    del self._active_operations[operation_type]

    def get_active_operations(self) -> Dict[str, int]:
        """Get current active operations count."""
        with self._resource_lock:
            return dict(self._active_operations)

    def update_worker_count(self, count: int) -> None:
        """Thread-safe worker count update."""
        with self._worker_count_lock:
            global _current_worker_count
            _current_worker_count = count

    def get_worker_count(self) -> Optional[int]:
        """Thread-safe worker count retrieval."""
        with self._worker_count_lock:
            return _current_worker_count

    def record_performance_metric(self, operation: str, metric_name: str, value: float) -> None:
        """Thread-safe performance metric recording."""
        with self._performance_data_lock:
            if operation not in self._performance_metrics:
                self._performance_metrics[operation] = {}
            if metric_name not in self._performance_metrics[operation]:
                self._performance_metrics[operation][metric_name] = []

            self._performance_metrics[operation][metric_name].append({
                'value': value,
                'timestamp': time.time(),
                'thread_id': threading.current_thread().ident
            })

            # Keep only recent metrics (last 100 entries per metric)
            if len(self._performance_metrics[operation][metric_name]) > 100:
                self._performance_metrics[operation][metric_name] = \
                    self._performance_metrics[operation][metric_name][-100:]

    def get_performance_metrics(self, operation: str = None) -> Dict:
        """Thread-safe performance metrics retrieval."""
        with self._performance_data_lock:
            if operation:
                return self._performance_metrics.get(operation, {}).copy()
            return {k: v.copy() for k, v in self._performance_metrics.items()}

    def safe_memory_check(self) -> Dict[str, float]:
        """Thread-safe memory usage check with throttling."""
        current_time = time.time()

        with self._memory_stats_lock:
            if current_time - self._last_memory_check < self._check_interval:
                # Return cached result if checked recently
                if hasattr(self, '_cached_memory_stats'):
                    return self._cached_memory_stats

            try:
                memory = psutil.virtual_memory()
                process = psutil.Process()
                process_memory = process.memory_info()

                stats = {
                    'system_total_gb': memory.total / (1024**3),
                    'system_available_gb': memory.available / (1024**3),
                    'system_used_percent': memory.percent,
                    'process_rss_mb': process_memory.rss / (1024**2),
                    'process_vms_mb': process_memory.vms / (1024**2),
                    'timestamp': current_time
                }

                self._cached_memory_stats = stats
                self._last_memory_check = current_time
                return stats

            except Exception as e:
                logging.warning(f"Thread-safe memory check failed: {e}")
                return {'error': str(e), 'timestamp': current_time}

class ThreadSafeGraphProcessor:
    """
    Thread-safe graph processing utilities for parallel operations.
    Ensures graph state consistency across multiple threads.
    """

    def __init__(self):
        self._graph_locks = {}  # Per-graph locks
        self._global_lock = Lock()

    def get_graph_lock(self, graph_id: str) -> Lock:
        """Get or create a lock for a specific graph."""
        with self._global_lock:
            if graph_id not in self._graph_locks:
                self._graph_locks[graph_id] = Lock()
            return self._graph_locks[graph_id]

    @contextmanager
    def safe_graph_operation(self, graph_id: str):
        """Context manager for thread-safe graph operations."""
        graph_lock = self.get_graph_lock(graph_id)
        with graph_lock:
            yield

    def safe_graph_copy(self, graph, graph_id: str = None):
        """Thread-safe graph copying."""
        if graph_id is None:
            graph_id = f"graph_{id(graph)}"

        with self.safe_graph_operation(graph_id):
            try:
                return graph.copy()
            except Exception as e:
                logging.warning(f"Thread-safe graph copy failed: {e}")
                # Fallback: create new graph and copy nodes/edges manually
                import networkx as nx
                new_graph = nx.Graph()
                new_graph.add_nodes_from(graph.nodes(data=True))
                new_graph.add_edges_from(graph.edges(data=True))
                return new_graph

# Global thread-safe instances
_thread_safe_resource_manager = ThreadSafeResourceManager()
_thread_safe_graph_processor = ThreadSafeGraphProcessor()

# Thread-safe counters for algorithm calls
_thread_safe_greedy_calls = ThreadSafeCounter()
_thread_safe_local_calls = ThreadSafeCounter()
_thread_safe_sa_calls = ThreadSafeCounter()

def get_thread_safe_resource_manager() -> ThreadSafeResourceManager:
    """Get the global thread-safe resource manager."""
    return _thread_safe_resource_manager

def get_thread_safe_graph_processor() -> ThreadSafeGraphProcessor:
    """Get the global thread-safe graph processor."""
    return _thread_safe_graph_processor

#==============================================================================
#                           5. ROBUST ERROR HANDLING WITH FALLBACK STRATEGIES
#==============================================================================

class AlgorithmError(Exception):
    """Base exception for algorithm-related errors."""
    pass

class MemoryPressureError(AlgorithmError):
    """Exception raised when memory pressure is detected."""
    pass

class ParallelProcessingError(AlgorithmError):
    """Exception raised when parallel processing fails."""
    pass

class GraphIntegrityError(AlgorithmError):
    """Exception raised when graph integrity is compromised."""
    pass

class RobustErrorHandler:
    """
    Comprehensive error handling system with specific recovery strategies
    for different error types and graceful degradation capabilities.
    """

    def __init__(self):
        self.error_history = []
        self.recovery_strategies = {
            'memory_pressure': self._handle_memory_pressure,
            'parallel_failure': self._handle_parallel_failure,
            'graph_integrity': self._handle_graph_integrity,
            'timeout': self._handle_timeout,
            'dependency_missing': self._handle_dependency_missing,
            'system_instability': self._handle_system_instability
        }
        self.retry_counts = defaultdict(int)
        self.max_retries = 3
        self.exponential_backoff_base = 1.0

    def handle_error_with_recovery(self, error: Exception, operation_context: Dict[str, Any]) -> Any:
        """
        Handle errors with appropriate recovery strategies.

        Args:
            error: The exception that occurred
            operation_context: Context information about the operation

        Returns:
            Recovery result or raises if recovery fails
        """
        error_type = self._classify_error(error)
        operation_id = operation_context.get('operation_id', 'unknown')

        # Record error for analysis
        self._record_error(error, error_type, operation_context)

        # Check retry limits
        if self.retry_counts[operation_id] >= self.max_retries:
            logging.error(f"Maximum retries ({self.max_retries}) exceeded for operation {operation_id}")
            raise error

        # Apply exponential backoff
        backoff_time = self.exponential_backoff_base * (2 ** self.retry_counts[operation_id])
        if backoff_time > 0.1:  # Only sleep if significant
            time.sleep(min(backoff_time, 5.0))  # Cap at 5 seconds

        self.retry_counts[operation_id] += 1

        # Apply recovery strategy
        if error_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[error_type](error, operation_context)
            except Exception as recovery_error:
                logging.error(f"Recovery strategy failed for {error_type}: {recovery_error}")
                # Try fallback to sequential processing
                return self._fallback_to_sequential(operation_context)
        else:
            # Unknown error type - try generic recovery
            return self._generic_recovery(error, operation_context)

    def _classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate recovery strategy."""
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()

        if isinstance(error, MemoryError) or 'memory' in error_str or 'out of memory' in error_str:
            return 'memory_pressure'
        elif isinstance(error, (concurrent.futures.TimeoutError, TimeoutError)) or 'timeout' in error_str:
            return 'timeout'
        elif isinstance(error, (concurrent.futures.ProcessPoolExecutor, multiprocessing.ProcessError)) or 'process' in error_str:
            return 'parallel_failure'
        elif isinstance(error, ImportError) or 'import' in error_str or 'module' in error_str:
            return 'dependency_missing'
        elif 'graph' in error_str or 'networkx' in error_str or isinstance(error, GraphIntegrityError):
            return 'graph_integrity'
        elif 'cpu' in error_str or 'system' in error_str or 'resource' in error_str:
            return 'system_instability'
        else:
            return 'unknown'

    def _record_error(self, error: Exception, error_type: str, context: Dict[str, Any]) -> None:
        """Record error for analysis and pattern detection."""
        error_record = {
            'timestamp': time.time(),
            'error_type': error_type,
            'error_class': type(error).__name__,
            'error_message': str(error),
            'context': context.copy(),
            'traceback': traceback.format_exc()
        }

        self.error_history.append(error_record)

        # Keep only recent errors (last 100)
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]

        logging.warning(f"Error recorded: {error_type} - {str(error)}")

    def _handle_memory_pressure(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle memory pressure errors."""
        logging.warning("Handling memory pressure - triggering aggressive cleanup")

        # Trigger aggressive memory cleanup
        cleanup_stats = proactive_memory_cleanup(force_aggressive=True)

        # Reduce parallelization
        if 'max_workers' in context:
            context['max_workers'] = 1
            logging.info("Reduced to single worker due to memory pressure")

        # Switch to memory-efficient algorithms
        if 'algorithm' in context:
            context['use_memory_efficient'] = True
            context['use_vectorization'] = False
            logging.info("Switched to memory-efficient algorithms")

        # Retry the operation with modified context
        return self._retry_operation_with_context(context)

    def _handle_parallel_failure(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle parallel processing failures."""
        logging.warning("Handling parallel processing failure - falling back to sequential")

        # Force sequential processing
        context['max_workers'] = 1
        context['use_parallel'] = False

        # Retry with sequential processing
        return self._retry_operation_with_context(context)

    def _handle_graph_integrity(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle graph integrity errors."""
        logging.warning("Handling graph integrity error - validating and repairing graph")

        # Try to validate and repair the graph
        if 'graph' in context:
            try:
                graph = context['graph']
                # Basic validation
                if not nx.is_connected(graph):
                    logging.error("Graph is not connected - cannot proceed")
                    raise GraphIntegrityError("Graph connectivity lost")

                # Check for self-loops and multi-edges
                if graph.number_of_selfloops() > 0:
                    graph.remove_edges_from(nx.selfloop_edges(graph))
                    logging.info("Removed self-loops from graph")

                context['graph'] = graph

            except Exception as repair_error:
                logging.error(f"Graph repair failed: {repair_error}")
                raise GraphIntegrityError("Cannot repair graph integrity")

        return self._retry_operation_with_context(context)

    def _handle_timeout(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle timeout errors."""
        logging.warning("Handling timeout - reducing problem complexity")

        # Increase timeout for retry
        if 'timeout' in context:
            context['timeout'] = min(context['timeout'] * 1.5, 1800)  # Cap at 30 minutes

        # Reduce algorithm complexity
        if 'max_iterations' in context:
            context['max_iterations'] = max(100, context['max_iterations'] // 2)

        # Reduce parallelization
        if 'max_workers' in context and context['max_workers'] > 1:
            context['max_workers'] = max(1, context['max_workers'] // 2)

        return self._retry_operation_with_context(context)

    def _handle_dependency_missing(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle missing dependency errors."""
        logging.warning("Handling missing dependency - switching to fallback implementation")

        # Disable features that require missing dependencies
        context['use_vectorization'] = False
        context['use_scipy'] = False
        context['use_memory_profiler'] = False

        # Force basic implementations
        context['force_basic_algorithms'] = True

        return self._retry_operation_with_context(context)

    def _handle_system_instability(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle system instability errors."""
        logging.warning("Handling system instability - switching to conservative mode")

        # Switch to most conservative settings
        context['max_workers'] = 1
        context['use_parallel'] = False
        context['safety_margin'] = 0.3  # Very conservative
        context['force_conservative'] = True

        # Trigger system cleanup
        emergency_resource_cleanup()

        return self._retry_operation_with_context(context)

    def _generic_recovery(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Generic recovery strategy for unknown errors."""
        logging.warning(f"Applying generic recovery for unknown error: {type(error).__name__}")

        # Apply conservative settings
        context['max_workers'] = 1
        context['use_parallel'] = False
        context['use_vectorization'] = False
        context['safety_margin'] = 0.5

        return self._retry_operation_with_context(context)

    def _fallback_to_sequential(self, context: Dict[str, Any]) -> Any:
        """Ultimate fallback to sequential processing."""
        logging.info("Applying ultimate fallback to sequential processing")

        # Most conservative settings possible
        context.update({
            'max_workers': 1,
            'use_parallel': False,
            'use_vectorization': False,
            'use_memory_efficient': True,
            'force_sequential': True,
            'safety_margin': 0.3
        })

        return self._retry_operation_with_context(context)

    def _retry_operation_with_context(self, context: Dict[str, Any]) -> Any:
        """Retry the operation with modified context."""
        operation_func = context.get('operation_func')
        operation_args = context.get('operation_args', ())
        operation_kwargs = context.get('operation_kwargs', {})

        if operation_func is None:
            raise AlgorithmError("No operation function provided for retry")

        # Update kwargs with modified context
        operation_kwargs.update({k: v for k, v in context.items()
                               if k not in ['operation_func', 'operation_args', 'operation_kwargs', 'operation_id']})

        try:
            return operation_func(*operation_args, **operation_kwargs)
        except Exception as retry_error:
            logging.error(f"Retry failed: {retry_error}")
            raise retry_error

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        if not self.error_history:
            return {'total_errors': 0}

        error_types = defaultdict(int)
        recent_errors = 0
        current_time = time.time()

        for error_record in self.error_history:
            error_types[error_record['error_type']] += 1
            if current_time - error_record['timestamp'] < 3600:  # Last hour
                recent_errors += 1

        return {
            'total_errors': len(self.error_history),
            'recent_errors_1h': recent_errors,
            'error_types': dict(error_types),
            'most_common_error': max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }

# Global error handler instance
_robust_error_handler = RobustErrorHandler()

def get_robust_error_handler() -> RobustErrorHandler:
    """Get the global robust error handler."""
    return _robust_error_handler

#==============================================================================
#                           6. RUNTIME CONSISTENCY TESTING
#==============================================================================

class ConsistencyTestError(Exception):
    """Exception raised when consistency tests fail."""
    pass

class RuntimeConsistencyTester:
    """
    Runtime consistency testing system that validates graph integrity
    and mathematical consistency during algorithm execution.
    """

    def __init__(self):
        self.test_history = []
        self.failed_tests = []
        self.test_intervals = {
            'graph_integrity': 10,  # Every 10 operations
            'cost_consistency': 5,   # Every 5 cost calculations
            'memory_integrity': 20,  # Every 20 operations
            'thread_safety': 15     # Every 15 parallel operations
        }
        self.operation_counts = defaultdict(int)
        self.consistency_lock = Lock()

    def should_run_test(self, test_type: str) -> bool:
        """Determine if a consistency test should be run."""
        with self.consistency_lock:
            self.operation_counts[test_type] += 1
            interval = self.test_intervals.get(test_type, 10)
            return self.operation_counts[test_type] % interval == 0

    def validate_graph_integrity(self, graph, operation_context: Dict[str, Any] = None) -> bool:
        """
        Validate graph integrity during algorithm execution.

        Args:
            graph: NetworkX graph to validate
            operation_context: Context information about the current operation

        Returns:
            bool: True if graph passes all integrity tests

        Raises:
            ConsistencyTestError: If critical integrity violations are found
        """
        if not self.should_run_test('graph_integrity'):
            return True

        test_results = []
        context = operation_context or {}

        try:
            # Test 1: Basic graph structure
            if not isinstance(graph, nx.Graph):
                test_results.append(('structure', False, "Not a valid NetworkX graph"))
            else:
                test_results.append(('structure', True, "Valid NetworkX graph"))

            # Test 2: Connectivity
            if graph.number_of_nodes() > 0:
                is_connected = nx.is_connected(graph)
                test_results.append(('connectivity', is_connected,
                                   "Graph is connected" if is_connected else "Graph is disconnected"))

                if not is_connected and context.get('require_connected', True):
                    raise ConsistencyTestError("Graph connectivity lost during operation")

            # Test 3: Tree properties (if expected to be a tree)
            if context.get('should_be_tree', False):
                is_tree = nx.is_tree(graph)
                test_results.append(('tree_property', is_tree,
                                   "Valid tree structure" if is_tree else "Not a valid tree"))

                if not is_tree:
                    # Additional diagnostics
                    num_nodes = graph.number_of_nodes()
                    num_edges = graph.number_of_edges()
                    expected_edges = num_nodes - 1

                    if num_edges != expected_edges:
                        test_results.append(('edge_count', False,
                                           f"Wrong edge count: {num_edges} (expected: {expected_edges})"))

                    if not is_connected:
                        test_results.append(('tree_connectivity', False, "Tree is not connected"))

                    # Check for cycles
                    try:
                        cycles = list(nx.simple_cycles(graph.to_directed()))
                        if cycles:
                            test_results.append(('cycles', False, f"Found {len(cycles)} cycles"))
                    except:
                        pass  # Ignore cycle detection errors

            # Test 4: Node and edge data integrity
            node_data_valid = True
            edge_data_valid = True

            for node, data in graph.nodes(data=True):
                if not isinstance(data, dict):
                    node_data_valid = False
                    break

            for u, v, data in graph.edges(data=True):
                if not isinstance(data, dict):
                    edge_data_valid = False
                    break
                # Check for valid weight
                if 'weight' in data:
                    try:
                        weight = float(data['weight'])
                        if weight < 0 or not math.isfinite(weight):
                            edge_data_valid = False
                            break
                    except (ValueError, TypeError):
                        edge_data_valid = False
                        break

            test_results.append(('node_data', node_data_valid,
                               "Node data valid" if node_data_valid else "Invalid node data"))
            test_results.append(('edge_data', edge_data_valid,
                               "Edge data valid" if edge_data_valid else "Invalid edge data"))

            # Test 5: Self-loops and multi-edges
            self_loops = list(nx.selfloop_edges(graph))
            has_self_loops = len(self_loops) > 0
            test_results.append(('self_loops', not has_self_loops,
                               "No self-loops" if not has_self_loops else f"Found {len(self_loops)} self-loops"))

            # Record test results
            self._record_test_results('graph_integrity', test_results, context)

            # Check for critical failures
            critical_failures = [result for result in test_results
                                if not result[1] and result[0] in ['structure', 'connectivity']]

            if critical_failures and context.get('strict_validation', False):
                failure_messages = [result[2] for result in critical_failures]
                raise ConsistencyTestError(f"Critical graph integrity failures: {'; '.join(failure_messages)}")

            # Return overall success
            return all(result[1] for result in test_results)

        except Exception as e:
            if isinstance(e, ConsistencyTestError):
                raise
            else:
                logging.warning(f"Graph integrity validation failed: {e}")
                self._record_test_results('graph_integrity', [('validation_error', False, str(e))], context)
                return False

    def validate_cost_consistency(self, graph, calculated_cost: float,
                                max_children: int, penalty: float,
                                operation_context: Dict[str, Any] = None) -> bool:
        """
        Validate cost calculation consistency.

        Args:
            graph: Graph for which cost was calculated
            calculated_cost: The calculated cost value
            max_children: Maximum children constraint
            penalty: Penalty value
            operation_context: Context information

        Returns:
            bool: True if cost calculation is consistent
        """
        if not self.should_run_test('cost_consistency'):
            return True

        test_results = []
        context = operation_context or {}

        try:
            # Test 1: Cost value validity
            is_finite = math.isfinite(calculated_cost)
            is_non_negative = calculated_cost >= 0

            test_results.append(('cost_finite', is_finite,
                               "Cost is finite" if is_finite else f"Cost is not finite: {calculated_cost}"))
            test_results.append(('cost_non_negative', is_non_negative,
                               "Cost is non-negative" if is_non_negative else f"Cost is negative: {calculated_cost}"))

            # Test 2: Recalculate cost independently
            try:
                recalculated_cost = self._independent_cost_calculation(graph, max_children, penalty)
                cost_difference = abs(calculated_cost - recalculated_cost)
                tolerance = max(0.01, calculated_cost * 0.001)  # 0.1% tolerance or 0.01 minimum

                costs_match = cost_difference <= tolerance
                test_results.append(('cost_recalculation', costs_match,
                                   f"Cost matches recalculation (diff: {cost_difference:.6f})" if costs_match
                                   else f"Cost mismatch: {calculated_cost} vs {recalculated_cost} (diff: {cost_difference:.6f})"))

                if not costs_match and context.get('strict_cost_validation', False):
                    raise ConsistencyTestError(f"Cost calculation inconsistency: {calculated_cost} vs {recalculated_cost}")

            except Exception as calc_error:
                test_results.append(('cost_recalculation', False, f"Recalculation failed: {calc_error}"))

            # Test 3: Constraint violation consistency
            if max_children != float('inf'):
                try:
                    violation_count = self._count_constraint_violations(graph, max_children)
                    expected_penalty_cost = violation_count * penalty

                    # Extract base cost (without penalties)
                    base_cost = sum(data.get('weight', 1) for _, _, data in graph.edges(data=True))
                    expected_total_cost = base_cost + expected_penalty_cost

                    penalty_consistent = abs(calculated_cost - expected_total_cost) <= tolerance
                    test_results.append(('penalty_consistency', penalty_consistent,
                                       f"Penalty calculation consistent" if penalty_consistent
                                       else f"Penalty inconsistent: expected {expected_total_cost}, got {calculated_cost}"))

                except Exception as penalty_error:
                    test_results.append(('penalty_consistency', False, f"Penalty validation failed: {penalty_error}"))

            # Record test results
            self._record_test_results('cost_consistency', test_results, context)

            # Check for critical failures
            critical_failures = [result for result in test_results
                                if not result[1] and result[0] in ['cost_finite', 'cost_non_negative']]

            if critical_failures:
                failure_messages = [result[2] for result in critical_failures]
                raise ConsistencyTestError(f"Critical cost consistency failures: {'; '.join(failure_messages)}")

            return all(result[1] for result in test_results)

        except Exception as e:
            if isinstance(e, ConsistencyTestError):
                raise
            else:
                logging.warning(f"Cost consistency validation failed: {e}")
                self._record_test_results('cost_consistency', [('validation_error', False, str(e))], context)
                return False

    def validate_memory_integrity(self, operation_context: Dict[str, Any] = None) -> bool:
        """
        Validate memory integrity during algorithm execution.

        Args:
            operation_context: Context information about the current operation

        Returns:
            bool: True if memory state is consistent
        """
        if not self.should_run_test('memory_integrity'):
            return True

        test_results = []
        context = operation_context or {}

        try:
            # Test 1: Memory usage within reasonable bounds
            memory_stats = monitor_memory_usage()

            if 'error' not in memory_stats:
                system_usage = memory_stats['system_used_percent']
                process_rss = memory_stats['process_rss_mb']

                reasonable_system_usage = system_usage < 95.0
                reasonable_process_usage = process_rss < 2048  # 2GB limit for process

                test_results.append(('system_memory', reasonable_system_usage,
                                   f"System memory usage OK: {system_usage:.1f}%" if reasonable_system_usage
                                   else f"High system memory usage: {system_usage:.1f}%"))

                test_results.append(('process_memory', reasonable_process_usage,
                                   f"Process memory usage OK: {process_rss:.1f}MB" if reasonable_process_usage
                                   else f"High process memory usage: {process_rss:.1f}MB"))
            else:
                test_results.append(('memory_monitoring', False, f"Memory monitoring failed: {memory_stats['error']}"))

            # Test 2: Garbage collection effectiveness
            gc_before = len(gc.get_objects())
            gc.collect()
            gc_after = len(gc.get_objects())

            objects_freed = gc_before - gc_after
            gc_effective = objects_freed >= 0  # Should not increase

            test_results.append(('garbage_collection', gc_effective,
                               f"GC freed {objects_freed} objects" if gc_effective
                               else f"GC issue: object count increased by {-objects_freed}"))

            # Record test results
            self._record_test_results('memory_integrity', test_results, context)

            return all(result[1] for result in test_results)

        except Exception as e:
            logging.warning(f"Memory integrity validation failed: {e}")
            self._record_test_results('memory_integrity', [('validation_error', False, str(e))], context)
            return False

    def _independent_cost_calculation(self, graph, max_children: int, penalty: float) -> float:
        """Independent cost calculation for validation."""
        try:
            # Calculate base cost (sum of edge weights)
            base_cost = 0.0
            for _, _, data in graph.edges(data=True):
                weight = data.get('weight', 1.0)
                base_cost += float(weight)

            # Calculate constraint violations
            violation_cost = 0.0
            if max_children != float('inf'):
                violation_count = self._count_constraint_violations(graph, max_children)
                violation_cost = violation_count * penalty

            return base_cost + violation_cost

        except Exception as e:
            logging.warning(f"Independent cost calculation failed: {e}")
            return float('inf')

    def _count_constraint_violations(self, graph, max_children: int) -> int:
        """Count constraint violations in the graph."""
        violations = 0
        degrees = dict(graph.degree())

        for node in graph.nodes():
            # Count children (nodes with lower degree connected to this node)
            children_count = 0
            node_degree = degrees[node]

            for neighbor in graph.neighbors(node):
                neighbor_degree = degrees[neighbor]
                if neighbor_degree < node_degree:
                    children_count += 1
                elif neighbor_degree == node_degree and node < neighbor:
                    # Tie-breaking rule for equal degrees
                    children_count += 1

            if children_count > max_children:
                violations += children_count - max_children

        return violations

    def _record_test_results(self, test_type: str, results: List[Tuple], context: Dict[str, Any]) -> None:
        """Record test results for analysis."""
        test_record = {
            'timestamp': time.time(),
            'test_type': test_type,
            'results': results,
            'context': context.copy(),
            'thread_id': threading.current_thread().ident,
            'success': all(result[1] for result in results)
        }

        with self.consistency_lock:
            self.test_history.append(test_record)

            # Track failed tests separately
            if not test_record['success']:
                self.failed_tests.append(test_record)

            # Keep only recent history (last 1000 tests)
            if len(self.test_history) > 1000:
                self.test_history = self.test_history[-1000:]

            # Keep only recent failed tests (last 100)
            if len(self.failed_tests) > 100:
                self.failed_tests = self.failed_tests[-100:]

    def get_test_statistics(self) -> Dict[str, Any]:
        """Get comprehensive test statistics."""
        with self.consistency_lock:
            if not self.test_history:
                return {'total_tests': 0}

            total_tests = len(self.test_history)
            failed_tests = len(self.failed_tests)
            success_rate = (total_tests - failed_tests) / total_tests if total_tests > 0 else 0.0

            # Count tests by type
            test_type_counts = defaultdict(int)
            test_type_failures = defaultdict(int)

            for test_record in self.test_history:
                test_type_counts[test_record['test_type']] += 1
                if not test_record['success']:
                    test_type_failures[test_record['test_type']] += 1

            # Recent test performance (last hour)
            current_time = time.time()
            recent_tests = [t for t in self.test_history if current_time - t['timestamp'] < 3600]
            recent_failures = [t for t in self.failed_tests if current_time - t['timestamp'] < 3600]

            return {
                'total_tests': total_tests,
                'failed_tests': failed_tests,
                'success_rate': success_rate,
                'test_type_counts': dict(test_type_counts),
                'test_type_failures': dict(test_type_failures),
                'recent_tests_1h': len(recent_tests),
                'recent_failures_1h': len(recent_failures),
                'most_common_failure': max(test_type_failures.items(), key=lambda x: x[1])[0] if test_type_failures else None
            }

    def reset_test_history(self) -> None:
        """Reset test history and statistics."""
        with self.consistency_lock:
            self.test_history.clear()
            self.failed_tests.clear()
            self.operation_counts.clear()
            logging.info("Runtime consistency test history reset")

# Global consistency tester instance
_runtime_consistency_tester = RuntimeConsistencyTester()

def get_runtime_consistency_tester() -> RuntimeConsistencyTester:
    """Get the global runtime consistency tester."""
    return _runtime_consistency_tester

def validate_algorithm_state(graph, cost: float = None, max_children: int = None,
                           penalty: float = None, operation_context: Dict[str, Any] = None) -> bool:
    """
    Convenience function to validate algorithm state during execution.

    Args:
        graph: Graph to validate
        cost: Calculated cost (optional)
        max_children: Maximum children constraint (optional)
        penalty: Penalty value (optional)
        operation_context: Context information (optional)

    Returns:
        bool: True if all validations pass
    """
    tester = get_runtime_consistency_tester()
    context = operation_context or {}

    try:
        # Always validate graph integrity
        graph_valid = tester.validate_graph_integrity(graph, context)

        # Validate cost if provided
        cost_valid = True
        if cost is not None and max_children is not None and penalty is not None:
            cost_valid = tester.validate_cost_consistency(graph, cost, max_children, penalty, context)

        # Validate memory integrity
        memory_valid = tester.validate_memory_integrity(context)

        return graph_valid and cost_valid and memory_valid

    except ConsistencyTestError as e:
        logging.error(f"Consistency validation failed: {e}")
        return False
    except Exception as e:
        logging.warning(f"Validation error: {e}")
        return False

#==============================================================================
#                           7. ADVANCED ADAPTIVE MEMORY MANAGEMENT
#==============================================================================

class AdvancedMemoryManager:
    """
    Advanced adaptive memory management system that enhances existing
    memory management with dynamic thresholds and predictive cleanup.
    """

    def __init__(self):
        self.memory_history = []
        self.cleanup_history = []
        self.memory_lock = Lock()
        self.prediction_window = 10  # Number of samples for prediction
        self.dynamic_thresholds = {
            'warning': 70.0,      # Warning threshold (%)
            'critical': 85.0,     # Critical threshold (%)
            'emergency': 95.0     # Emergency threshold (%)
        }
        self.adaptive_cleanup_intervals = {
            'light': 50,          # Light cleanup every 50 operations
            'moderate': 20,       # Moderate cleanup every 20 operations
            'aggressive': 5       # Aggressive cleanup every 5 operations
        }
        self.operation_count = 0
        self.last_cleanup_time = time.time()

    def get_dynamic_memory_thresholds(self) -> Dict[str, float]:
        """Calculate dynamic memory thresholds based on system state and history."""
        try:
            # Get current system state
            cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()

            # Adjust thresholds based on available RAM
            if available_ram_gb < 2.0:
                # Very low memory system - be more aggressive
                return {
                    'warning': 60.0,
                    'critical': 75.0,
                    'emergency': 90.0
                }
            elif available_ram_gb < 4.0:
                # Low memory system - be moderately aggressive
                return {
                    'warning': 65.0,
                    'critical': 80.0,
                    'emergency': 92.0
                }
            elif available_ram_gb > 16.0:
                # High memory system - be more relaxed
                return {
                    'warning': 80.0,
                    'critical': 90.0,
                    'emergency': 97.0
                }
            else:
                # Standard system - use default thresholds
                return self.dynamic_thresholds.copy()

        except Exception as e:
            logging.warning(f"Failed to calculate dynamic thresholds: {e}")
            return self.dynamic_thresholds.copy()

# Global advanced memory manager instance
_advanced_memory_manager = AdvancedMemoryManager()

def get_advanced_memory_manager() -> AdvancedMemoryManager:
    """Get the global advanced memory manager."""
    return _advanced_memory_manager

#==============================================================================
#                           9. SAFE EDGE WEIGHT ACCESS UTILITIES
#==============================================================================

def safe_get_edge_weight(G, u, v, default_weight=1):
    """
    Safely get edge weight from graph, handling missing edges and weights.

    Args:
        G: NetworkX graph
        u, v: Edge endpoints
        default_weight: Default weight if edge or weight doesn't exist

    Returns:
        float: Edge weight or default weight
    """
    try:
        if G.has_edge(u, v):
            edge_data = G[u][v]
            if isinstance(edge_data, dict) and 'weight' in edge_data:
                weight = edge_data['weight']
                # Ensure weight is a valid number
                if isinstance(weight, (int, float)) and weight > 0:
                    return float(weight)
                else:
                    logging.debug(f"Invalid weight {weight} for edge ({u}, {v}), using default {default_weight}")
                    return float(default_weight)
            else:
                logging.debug(f"No weight attribute for edge ({u}, {v}), using default {default_weight}")
                return float(default_weight)
        else:
            logging.debug(f"Edge ({u}, {v}) does not exist, using default weight {default_weight}")
            return float(default_weight)
    except Exception as e:
        logging.warning(f"Error accessing weight for edge ({u}, {v}): {e}. Using default {default_weight}")
        return float(default_weight)

def safe_add_edge_with_weight(G, u, v, source_graph=None, default_weight=1):
    """
    Safely add edge to graph with proper weight handling.

    Args:
        G: Target graph to add edge to
        u, v: Edge endpoints
        source_graph: Source graph to get weight from (optional)
        default_weight: Default weight if no source or weight not found

    Returns:
        bool: True if edge was added successfully
    """
    try:
        # Get weight from source graph if provided
        if source_graph is not None:
            weight = safe_get_edge_weight(source_graph, u, v, default_weight)
        else:
            weight = default_weight

        # Add edge with weight
        G.add_edge(u, v, weight=weight)
        return True

    except Exception as e:
        logging.warning(f"Failed to add edge ({u}, {v}) with weight: {e}")
        return False

def validate_graph_weights(G, fix_missing=True, default_weight=1):
    """
    Validate and optionally fix missing or invalid edge weights in a graph.

    Args:
        G: NetworkX graph
        fix_missing: Whether to add missing weights
        default_weight: Default weight to use for missing weights

    Returns:
        tuple: (is_valid, num_fixed, errors)
    """
    is_valid = True
    num_fixed = 0
    errors = []

    try:
        for u, v, data in G.edges(data=True):
            if 'weight' not in data or data['weight'] is None:
                is_valid = False
                errors.append(f"Edge ({u}, {v}) missing weight")

                if fix_missing:
                    G[u][v]['weight'] = default_weight
                    num_fixed += 1
            elif not isinstance(data['weight'], (int, float)) or data['weight'] <= 0:
                is_valid = False
                errors.append(f"Edge ({u}, {v}) has invalid weight: {data['weight']}")

                if fix_missing:
                    G[u][v]['weight'] = default_weight
                    num_fixed += 1

    except Exception as e:
        logging.warning(f"Graph weight validation failed: {e}")
        errors.append(f"Validation error: {e}")

    return is_valid, num_fixed, errors

def enhanced_parallel_local_search(G, initial_tree, max_degree, penalty, num_threads=None, stop_event=None, queue=None):
    """
    Enhanced parallel local search - wrapper around parallel_local_search for backward compatibility.

    Args:
        G: NetworkX graph
        initial_tree: Initial spanning tree
        max_degree: Maximum degree constraint
        penalty: Penalty for violations
        num_threads: Number of threads to use
        stop_event: Event to signal stopping
        queue: Queue for progress updates

    Returns:
        tuple: (best_tree, total_calls, history)
    """
    return parallel_local_search(G, initial_tree, max_degree, penalty, num_threads, stop_event, queue)

#==============================================================================
#                           8. CRITICAL IMPROVEMENTS INITIALIZATION
#==============================================================================

def initialize_critical_improvements() -> bool:
    """
    Initialize all critical improvements at application startup.

    This function should be called at the beginning of the application
    to ensure all systems are properly initialized and verified.

    Returns:
        bool: True if all systems initialized successfully
    """
    initialization_results = []

    try:
        # 1. Verify dependencies
        logging.info("=== Initializing Critical Improvements ===")
        logging.info("1. Verifying dependencies...")

        try:
            dependency_success = verify_dependencies_at_startup()
            initialization_results.append(("dependency_verification", dependency_success))
            if dependency_success:
                logging.info("PASS Dependency verification completed successfully")
            else:
                logging.warning("WARN Dependency verification completed with warnings")
        except DependencyVerificationError as e:
            logging.error(f"FAIL Critical dependency verification failed: {e}")
            initialization_results.append(("dependency_verification", False))
            return False

        # 2. Initialize thread-safe systems
        logging.info("2. Initializing thread-safe systems...")
        try:
            resource_manager = get_thread_safe_resource_manager()
            graph_processor = get_thread_safe_graph_processor()

            # Test basic functionality
            with resource_manager.resource_operation("initialization_test"):
                pass

            initialization_results.append(("thread_safety", True))
            logging.info("PASS Thread-safe systems initialized successfully")
        except Exception as e:
            logging.error(f"FAIL Thread-safe system initialization failed: {e}")
            initialization_results.append(("thread_safety", False))

        # 3. Initialize error handling system
        logging.info("3. Initializing robust error handling...")
        try:
            error_handler = get_robust_error_handler()

            # Test error classification
            test_error = Exception("Test error for initialization")
            error_type = error_handler._classify_error(test_error)

            initialization_results.append(("error_handling", True))
            logging.info("PASS Robust error handling initialized successfully")
        except Exception as e:
            logging.error(f"FAIL Error handling initialization failed: {e}")
            initialization_results.append(("error_handling", False))

        # 4. Initialize runtime consistency testing
        logging.info("4. Initializing runtime consistency testing...")
        try:
            consistency_tester = get_runtime_consistency_tester()

            # Test basic validation functionality
            test_graph = nx.Graph()
            test_graph.add_edge(1, 2, weight=1.0)
            test_context = {'test_mode': True, 'strict_validation': False}

            validation_result = consistency_tester.validate_graph_integrity(test_graph, test_context)

            initialization_results.append(("consistency_testing", True))
            logging.info("PASS Runtime consistency testing initialized successfully")
        except Exception as e:
            logging.error(f"FAIL Consistency testing initialization failed: {e}")
            initialization_results.append(("consistency_testing", False))

        # 5. Initialize advanced memory management
        logging.info("5. Initializing advanced memory management...")
        try:
            memory_manager = get_advanced_memory_manager()

            # Test dynamic threshold calculation
            thresholds = memory_manager.get_dynamic_memory_thresholds()

            initialization_results.append(("memory_management", True))
            logging.info("PASS Advanced memory management initialized successfully")
        except Exception as e:
            logging.error(f"FAIL Memory management initialization failed: {e}")
            initialization_results.append(("memory_management", False))

        # 6. System resource detection and optimization
        logging.info("6. Detecting system resources and optimizing...")
        try:
            # Detect and log system capabilities
            cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()
            system_type, safety_margin, ram_efficiency = classify_system_type(cpu_cores, available_ram_gb)

            # Calculate optimal workers
            optimal_workers = calculate_optimal_workers()

            logging.info(f"PASS System optimization completed:")
            logging.info(f"  - System type: {system_type.upper()}")
            logging.info(f"  - CPU cores: {cpu_cores}")
            logging.info(f"  - Total RAM: {total_ram_gb:.1f}GB")
            logging.info(f"  - Available RAM: {available_ram_gb:.1f}GB")
            logging.info(f"  - Optimal workers: {optimal_workers}")
            logging.info(f"  - Safety margin: {safety_margin:.1%}")

            initialization_results.append(("system_optimization", True))
        except Exception as e:
            logging.error(f"FAIL System optimization failed: {e}")
            initialization_results.append(("system_optimization", False))

        # 7. Initialize dynamic thresholds
        logging.info("7. Initializing dynamic thresholds...")
        try:
            dynamic_thresholds = get_dynamic_thresholds()
            current_thresholds = dynamic_thresholds.get_current_thresholds()

            logging.info(f"PASS Dynamic thresholds initialized:")
            for threshold_name, value in current_thresholds.items():
                logging.info(f"  - {threshold_name}: {value}")

            initialization_results.append(("dynamic_thresholds", True))
        except Exception as e:
            logging.error(f"FAIL Dynamic thresholds initialization failed: {e}")
            initialization_results.append(("dynamic_thresholds", False))

        # Summary
        successful_systems = sum(1 for _, success in initialization_results if success)
        total_systems = len(initialization_results)

        logging.info("=== Critical Improvements Initialization Summary ===")
        logging.info(f"Successfully initialized: {successful_systems}/{total_systems} systems")

        for system_name, success in initialization_results:
            status = "PASS" if success else "FAIL"
            logging.info(f"{status} {system_name}")

        overall_success = successful_systems == total_systems

        if overall_success:
            logging.info("SUCCESS All critical improvements initialized successfully!")
            logging.info("The application is ready for enhanced performance and reliability.")
        else:
            logging.warning("WARN Some systems failed to initialize. The application will run with reduced capabilities.")

        return overall_success

    except Exception as e:
        logging.error(f"Critical failure during initialization: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return False

def get_system_status_summary() -> Dict[str, Any]:
    """
    Get a comprehensive summary of all system statuses.

    Returns:
        Dict containing status information for all critical systems
    """
    try:
        status = {
            'timestamp': time.time(),
            'dependency_verification': {},
            'thread_safety': {},
            'error_handling': {},
            'consistency_testing': {},
            'memory_management': {},
            'system_resources': {},
            'overall_health': 'unknown'
        }

        # Dependency verification status
        try:
            verifier = _dependency_verifier
            if verifier:
                status['dependency_verification'] = {
                    'available': True,
                    'results': verifier.verification_results,
                    'summary': verifier.get_verification_summary()
                }
            else:
                status['dependency_verification'] = {'available': False}
        except:
            status['dependency_verification'] = {'available': False, 'error': 'Failed to get status'}

        # Thread safety status
        try:
            resource_manager = get_thread_safe_resource_manager()
            status['thread_safety'] = {
                'available': True,
                'active_operations': resource_manager.get_active_operations(),
                'current_worker_count': resource_manager.get_worker_count(),
                'performance_metrics': resource_manager.get_performance_metrics()
            }
        except Exception as e:
            status['thread_safety'] = {'available': False, 'error': str(e)}

        # Error handling status
        try:
            error_handler = get_robust_error_handler()
            status['error_handling'] = {
                'available': True,
                'statistics': error_handler.get_error_statistics()
            }
        except Exception as e:
            status['error_handling'] = {'available': False, 'error': str(e)}

        # Consistency testing status
        try:
            consistency_tester = get_runtime_consistency_tester()
            status['consistency_testing'] = {
                'available': True,
                'statistics': consistency_tester.get_test_statistics()
            }
        except Exception as e:
            status['consistency_testing'] = {'available': False, 'error': str(e)}

        # Memory management status
        try:
            memory_stats = monitor_memory_usage()
            memory_manager = get_advanced_memory_manager()
            thresholds = memory_manager.get_dynamic_memory_thresholds()

            status['memory_management'] = {
                'available': True,
                'current_usage': memory_stats,
                'dynamic_thresholds': thresholds
            }
        except Exception as e:
            status['memory_management'] = {'available': False, 'error': str(e)}

        # System resources status
        try:
            cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()
            system_type, safety_margin, ram_efficiency = classify_system_type(cpu_cores, available_ram_gb)

            status['system_resources'] = {
                'available': True,
                'cpu_cores': cpu_cores,
                'total_ram_gb': total_ram_gb,
                'available_ram_gb': available_ram_gb,
                'system_type': system_type,
                'safety_margin': safety_margin,
                'ram_efficiency': ram_efficiency
            }
        except Exception as e:
            status['system_resources'] = {'available': False, 'error': str(e)}

        # Overall health assessment
        available_systems = sum(1 for system_status in status.values()
                              if isinstance(system_status, dict) and system_status.get('available', False))
        total_systems = len([k for k in status.keys() if k != 'timestamp' and k != 'overall_health'])

        if available_systems == total_systems:
            status['overall_health'] = 'excellent'
        elif available_systems >= total_systems * 0.8:
            status['overall_health'] = 'good'
        elif available_systems >= total_systems * 0.6:
            status['overall_health'] = 'fair'
        else:
            status['overall_health'] = 'poor'

        return status

    except Exception as e:
        return {
            'timestamp': time.time(),
            'overall_health': 'error',
            'error': str(e)
        }

#==============================================================================
#                           4. TEST INSTANCE INITIALIZATION
#==============================================================================
test_instance = {
    'graph': nx.Graph(),
    'red_nodes': [],
    'weights': {}
}

def initialize_test_instance():
    """Initialize a test graph instance with sample data"""
    G = nx.Graph()
    # Add nodes
    nodes = range(1, 6)
    for node in nodes:
        G.add_node(node)

    # Add edges with weights
    edges_with_weights = [
        (1, 2, 10), (1, 3, 15), (2, 3, 5),
        (2, 4, 8), (3, 4, 12), (3, 5, 20), (4, 5, 7)
    ]

    for u, v, w in edges_with_weights:
        G.add_edge(u, v, weight=w)

    # Define red nodes (with constraints)
    red_nodes = [1, 5]

    # Update test instance
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
    SIMPLIFIED: System classification stub for backward compatibility.

    Args:
        cpu_cores: Ignored (for compatibility)
        available_ram_gb: Ignored (for compatibility)

    Returns:
        tuple: Always returns simplified system type
    """
    # Always return simplified system type for educational purposes
    return "simplified", 0.5, 0.8

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
    SIMPLIFIED: Calculate workers using simple fixed-worker approach.

    This function is kept for backward compatibility but now uses the simplified system.

    Args:
        safety_margin: Ignored (for compatibility)
        min_ram_per_worker: Ignored (for compatibility)
        max_workers: Ignored (for compatibility)

    Returns:
        int: Simple worker count (2-4 based on CPU cores)
    """
    # Import simplified parallelization
    from .simple_parallelization import get_simple_worker_count

    # Use simplified worker calculation with a default item count
    return get_simple_worker_count(10)  # Use 10 as default for compatibility

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
    SIMPLIFIED: Worker limit stub for backward compatibility.

    Args:
        operation_type: Ignored (for compatibility)
        base_workers: Ignored (for compatibility)

    Returns:
        int: Simple fixed worker count
    """
    # Import simplified parallelization
    from .simple_parallelization import get_simple_worker_count

    # Use simplified worker calculation
    return get_simple_worker_count(10)  # Use 10 as default for compatibility

def adaptive_worker_adjustment(current_workers, cpu_threshold=90.0):
    """
    SIMPLIFIED: Worker adjustment stub for backward compatibility.

    Args:
        current_workers: Ignored (for compatibility)
        cpu_threshold: Ignored (for compatibility)

    Returns:
        int: Simple fixed worker count
    """
    # Import simplified parallelization
    from .simple_parallelization import get_simple_worker_count

    # Use simplified worker calculation
    return get_simple_worker_count(10)  # Use 10 as default for compatibility



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

def proactive_memory_cleanup(force_aggressive=False):
    """
    Proactive memory cleanup during algorithm execution.

    Args:
        force_aggressive: If True, performs more aggressive cleanup

    Returns:
        dict: Memory statistics before and after cleanup
    """
    try:
        import psutil
        process = psutil.Process()

        # Get memory usage before cleanup
        memory_before = process.memory_info().rss / (1024 * 1024)  # MB

        # Standard cleanup
        gc.collect()

        # OPTIMIZATION: Only perform aggressive cleanup if memory usage is actually high
        if force_aggressive and memory_before > 2048:  # Only for very high memory usage (2GB+)
            # More conservative aggressive cleanup for memory-constrained situations

            # Reduced GC cycles to minimize overhead
            for _ in range(2):  # Reduced from 3 to 2
                gc.collect()

            # OPTIMIZATION: Skip GC threshold adjustment to reduce overhead
            # The original threshold adjustment is too expensive for frequent calls

        # Get memory usage after cleanup
        memory_after = process.memory_info().rss / (1024 * 1024)  # MB
        memory_freed = memory_before - memory_after

        cleanup_stats = {
            'memory_before_mb': memory_before,
            'memory_after_mb': memory_after,
            'memory_freed_mb': memory_freed,
            'aggressive': force_aggressive
        }

        # OPTIMIZATION: Increased threshold and reduced logging level to minimize overhead
        if memory_freed > 50:  # Increased from 10MB to 50MB
            logging.debug(f"Memory cleanup freed {memory_freed:.1f}MB (before: {memory_before:.1f}MB, after: {memory_after:.1f}MB)")

        return cleanup_stats

    except Exception as e:
        logging.debug(f"Proactive memory cleanup failed: {e}")  # Changed from warning to debug
        return {'error': str(e)}

def monitor_memory_usage():
    """
    Monitor current memory usage and return statistics.

    Returns:
        dict: Memory usage statistics
    """
    try:
        import psutil

        # System memory
        system_memory = psutil.virtual_memory()

        # Process memory
        process = psutil.Process()
        process_memory = process.memory_info()

        stats = {
            'system_total_gb': system_memory.total / (1024**3),
            'system_available_gb': system_memory.available / (1024**3),
            'system_used_percent': system_memory.percent,
            'process_rss_mb': process_memory.rss / (1024**2),
            'process_vms_mb': process_memory.vms / (1024**2),
            'memory_pressure': system_memory.percent > 85,  # High memory usage
            'critical_memory': system_memory.percent > 95   # Critical memory usage
        }

        return stats

    except Exception as e:
        logging.warning(f"Memory monitoring failed: {e}")
        return {'error': str(e)}

def adaptive_memory_management(current_operation="general"):
    """
    Adaptive memory management based on current system state and operation.

    Args:
        current_operation: Type of operation being performed

    Returns:
        dict: Memory management recommendations
    """
    try:
        memory_stats = monitor_memory_usage()

        if 'error' in memory_stats:
            return {'action': 'continue', 'reason': 'monitoring_failed'}

        recommendations = {
            'action': 'continue',
            'cleanup_needed': False,
            'aggressive_cleanup': False,
            'reduce_workers': False,
            'fallback_sequential': False,
            'memory_stats': memory_stats
        }

        # Determine actions based on memory pressure
        if memory_stats['critical_memory']:
            # Critical memory situation
            recommendations.update({
                'action': 'emergency_cleanup',
                'cleanup_needed': True,
                'aggressive_cleanup': True,
                'reduce_workers': True,
                'fallback_sequential': True,
                'reason': f"Critical memory usage: {memory_stats['system_used_percent']:.1f}%"
            })
        elif memory_stats['memory_pressure']:
            # High memory pressure
            recommendations.update({
                'action': 'reduce_load',
                'cleanup_needed': True,
                'aggressive_cleanup': False,
                'reduce_workers': True,
                'fallback_sequential': False,
                'reason': f"High memory usage: {memory_stats['system_used_percent']:.1f}%"
            })
        elif memory_stats['system_used_percent'] > 70:
            # Moderate memory usage - proactive cleanup
            recommendations.update({
                'action': 'proactive_cleanup',
                'cleanup_needed': True,
                'aggressive_cleanup': False,
                'reduce_workers': False,
                'fallback_sequential': False,
                'reason': f"Moderate memory usage: {memory_stats['system_used_percent']:.1f}%"
            })

        # Operation-specific adjustments
        if current_operation in ['simulated_annealing', 'parallel_local_search']:
            # These operations are more memory-intensive
            if memory_stats['system_used_percent'] > 60:
                recommendations['cleanup_needed'] = True

        return recommendations

    except Exception as e:
        logging.warning(f"Adaptive memory management failed: {e}")
        return {'action': 'continue', 'error': str(e)}

# Efficient Data Structures for Large Graphs
class MemoryEfficientGraph:
    """
    Memory-efficient graph representation for very large graphs.
    Uses sparse data structures and lazy evaluation to minimize memory usage.
    """

    def __init__(self, networkx_graph=None):
        """Initialize from a NetworkX graph or create empty."""
        self.nodes = set()
        self.edges = {}  # adjacency list with edge weights
        self.node_count = 0
        self.edge_count = 0

        if networkx_graph:
            self._from_networkx(networkx_graph)

    def _from_networkx(self, G):
        """Convert from NetworkX graph to memory-efficient representation."""
        self.nodes = set(G.nodes())
        self.node_count = len(self.nodes)
        self.edge_count = G.number_of_edges()

        # Use sparse adjacency list
        self.edges = {}
        for node in self.nodes:
            self.edges[node] = {}

        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            self.edges[u][v] = weight
            self.edges[v][u] = weight  # Undirected graph

    def to_networkx(self):
        """Convert back to NetworkX graph when needed."""
        G = nx.Graph()
        G.add_nodes_from(self.nodes)

        # Add edges (avoid duplicates in undirected graph)
        added_edges = set()
        for u in self.edges:
            for v, weight in self.edges[u].items():
                edge = tuple(sorted([u, v]))
                if edge not in added_edges:
                    G.add_edge(u, v, weight=weight)
                    added_edges.add(edge)

        return G

    def has_edge(self, u, v):
        """Check if edge exists."""
        return u in self.edges and v in self.edges[u]

    def get_weight(self, u, v):
        """Get edge weight."""
        if self.has_edge(u, v):
            return self.edges[u][v]
        return None

    def neighbors(self, node):
        """Get neighbors of a node."""
        return self.edges.get(node, {}).keys()

    def degree(self, node):
        """Get degree of a node."""
        return len(self.edges.get(node, {}))

    def memory_usage_mb(self):
        """Estimate memory usage in MB."""
        try:
            import sys
            total_size = sys.getsizeof(self.nodes)
            total_size += sys.getsizeof(self.edges)

            for node_edges in self.edges.values():
                total_size += sys.getsizeof(node_edges)
                for neighbor, weight in node_edges.items():
                    total_size += sys.getsizeof(neighbor) + sys.getsizeof(weight)

            return total_size / (1024 * 1024)
        except:
            return 0.0

class CompactSpanningTree:
    """
    Compact representation of spanning trees for memory efficiency.
    Stores only essential information and computes derived properties on demand.
    """

    def __init__(self, edges=None, nodes=None):
        """Initialize with edge list and node set."""
        self.edges = set(edges) if edges else set()
        self.nodes = set(nodes) if nodes else set()
        self._adjacency = None  # Lazy computation
        self._degrees = None    # Lazy computation

        # Extract nodes from edges if not provided
        if not self.nodes and self.edges:
            for u, v in self.edges:
                self.nodes.add(u)
                self.nodes.add(v)

    def _build_adjacency(self):
        """Build adjacency list on demand."""
        if self._adjacency is None:
            self._adjacency = {node: set() for node in self.nodes}
            for u, v in self.edges:
                self._adjacency[u].add(v)
                self._adjacency[v].add(u)

    def _compute_degrees(self):
        """Compute node degrees on demand."""
        if self._degrees is None:
            self._build_adjacency()
            self._degrees = {node: len(neighbors) for node, neighbors in self._adjacency.items()}

    def neighbors(self, node):
        """Get neighbors of a node."""
        self._build_adjacency()
        return self._adjacency.get(node, set())

    def degree(self, node):
        """Get degree of a node."""
        self._compute_degrees()
        return self._degrees.get(node, 0)

    def is_connected(self):
        """Check if the tree is connected using DFS."""
        if not self.nodes:
            return True

        self._build_adjacency()
        visited = set()
        start_node = next(iter(self.nodes))

        def dfs(node):
            visited.add(node)
            for neighbor in self._adjacency[node]:
                if neighbor not in visited:
                    dfs(neighbor)

        dfs(start_node)
        return len(visited) == len(self.nodes)

    def to_networkx(self, original_graph=None):
        """Convert to NetworkX graph with edge weights from original graph."""
        G = nx.Graph()
        G.add_nodes_from(self.nodes)

        for u, v in self.edges:
            if original_graph and original_graph.has_edge(u, v):
                weight = safe_get_edge_weight(original_graph, u, v, default_weight=1)
            else:
                weight = 1
            G.add_edge(u, v, weight=weight)

        return G

    def memory_usage_mb(self):
        """Estimate memory usage in MB."""
        try:
            import sys
            total_size = sys.getsizeof(self.edges) + sys.getsizeof(self.nodes)
            if self._adjacency:
                total_size += sys.getsizeof(self._adjacency)
                for neighbors in self._adjacency.values():
                    total_size += sys.getsizeof(neighbors)
            if self._degrees:
                total_size += sys.getsizeof(self._degrees)
            return total_size / (1024 * 1024)
        except:
            return 0.0

def create_efficient_graph_representation(G, force_compact=False):
    """
    Create memory-efficient graph representation based on graph size.

    Args:
        G: NetworkX graph
        force_compact: Force use of compact representation

    Returns:
        Efficient graph representation or original graph
    """
    try:
        graph_size = len(G.nodes())
        edge_count = len(G.edges())

        # Determine if we need efficient representation using dynamic thresholds
        dynamic_thresholds = get_dynamic_thresholds()
        memory_stats = monitor_memory_usage()

        use_efficient = (
            force_compact or
            dynamic_thresholds.should_use_memory_efficient(graph_size) or
            edge_count > 2000 or
            (memory_stats and memory_stats.get('memory_pressure', False))
        )

        if use_efficient:
            logging.info(f"Using memory-efficient representation for graph ({graph_size} nodes, {edge_count} edges)")
            return MemoryEfficientGraph(G)
        else:
            return G

    except Exception as e:
        logging.warning(f"Failed to create efficient representation: {e}")
        return G









# Dynamic Graph Size Thresholds Implementation
class DynamicGraphThresholds:
    """
    Dynamic graph size thresholds that adapt to system capabilities.

    Features:
    - Automatic threshold calculation based on system resources
    - Performance-based threshold adjustment
    - Hardware-specific optimization
    - Real-time threshold adaptation
    """

    def __init__(self):
        """Initialize dynamic thresholds with system detection."""
        self.system_detected = False
        self.cpu_cores = 1
        self.total_ram_gb = 1.0
        self.available_ram_gb = 1.0
        self.system_type = "laptop"

        # Base thresholds (conservative defaults)
        self.base_thresholds = {
            "large_graph": 500,
            "parallel_min": 50,
            "sequential_force": 8000,
            "memory_efficient": 200,
            "ultra_fast_generation": True
        }

        # Current adaptive thresholds
        self.current_thresholds = self.base_thresholds.copy()

        # Performance history for adaptive adjustment
        self.performance_history = []
        self.threshold_adjustments = {}

        # Initialize system detection
        self._detect_system_capabilities()
        self._calculate_adaptive_thresholds()

    def _detect_system_capabilities(self):
        """Detect system capabilities for threshold calculation."""
        try:
            self.cpu_cores, self.total_ram_gb, self.available_ram_gb = detect_system_resources()
            self.system_type, _, _ = classify_system_type(self.cpu_cores, self.available_ram_gb)
            self.system_detected = True

            logging.info(f"Dynamic thresholds: System detected - {self.system_type.upper()} "
                        f"({self.cpu_cores} cores, {self.available_ram_gb:.1f}GB available)")
        except Exception as e:
            logging.warning(f"Failed to detect system for dynamic thresholds: {e}")
            self.system_detected = False

    def _calculate_adaptive_thresholds(self):
        """Calculate adaptive thresholds based on system capabilities."""
        if not self.system_detected:
            return

        # System-specific threshold multipliers
        if self.system_type == "workstation":
            # High-end workstation: aggressive parallelization
            multipliers = {
                "large_graph": 0.6,      # 300 nodes
                "parallel_min": 0.4,     # 20 nodes
                "sequential_force": 3.0,  # 24000 nodes
                "memory_efficient": 0.5   # 100 nodes
            }
        elif self.system_type == "desktop":
            # Desktop: balanced approach
            multipliers = {
                "large_graph": 0.8,      # 400 nodes
                "parallel_min": 0.6,     # 30 nodes
                "sequential_force": 2.0,  # 16000 nodes
                "memory_efficient": 0.75  # 150 nodes
            }
        else:  # laptop
            # Laptop: conservative approach
            multipliers = {
                "large_graph": 1.2,      # 600 nodes
                "parallel_min": 1.5,     # 75 nodes
                "sequential_force": 1.0,  # 8000 nodes
                "memory_efficient": 1.0   # 200 nodes
            }

        # Apply RAM-based adjustments
        ram_factor = min(2.0, max(0.5, self.available_ram_gb / 8.0))  # Normalize to 8GB baseline

        # Apply CPU-based adjustments
        cpu_factor = min(2.0, max(0.5, self.cpu_cores / 4.0))  # Normalize to 4 cores baseline

        # Calculate adaptive thresholds
        for threshold_name, base_value in self.base_thresholds.items():
            if threshold_name == "ultra_fast_generation":
                # Enable ultra-fast generation on powerful systems
                self.current_thresholds[threshold_name] = (
                    self.system_type in ["workstation", "desktop"] and
                    self.cpu_cores >= 4 and
                    self.available_ram_gb >= 4.0
                )
            elif threshold_name in multipliers:
                # Apply system-specific and resource-based multipliers
                system_multiplier = multipliers[threshold_name]
                resource_multiplier = (ram_factor + cpu_factor) / 2.0
                final_multiplier = (system_multiplier + resource_multiplier) / 2.0

                self.current_thresholds[threshold_name] = int(base_value * final_multiplier)
            else:
                self.current_thresholds[threshold_name] = base_value

        # Ensure logical threshold ordering
        self._validate_threshold_consistency()

        logging.info(f"Dynamic thresholds calculated: {self.current_thresholds}")

    def _validate_threshold_consistency(self):
        """Ensure thresholds maintain logical relationships."""
        # Ensure parallel_min < large_graph < sequential_force
        if self.current_thresholds["parallel_min"] >= self.current_thresholds["large_graph"]:
            self.current_thresholds["parallel_min"] = max(10, self.current_thresholds["large_graph"] // 4)

        if self.current_thresholds["large_graph"] >= self.current_thresholds["sequential_force"]:
            self.current_thresholds["sequential_force"] = self.current_thresholds["large_graph"] * 2

        # Ensure memory_efficient threshold is reasonable
        if self.current_thresholds["memory_efficient"] >= self.current_thresholds["large_graph"]:
            self.current_thresholds["memory_efficient"] = max(50, self.current_thresholds["large_graph"] // 2)

    def get_threshold(self, threshold_name):
        """Get a specific threshold value."""
        return self.current_thresholds.get(threshold_name, self.base_thresholds.get(threshold_name, 500))

    def should_use_parallel(self, graph_size):
        """Determine if parallel processing should be used for given graph size."""
        return (graph_size >= self.get_threshold("parallel_min") and
                graph_size < self.get_threshold("sequential_force"))

    def should_use_memory_efficient(self, graph_size):
        """Determine if memory-efficient structures should be used."""
        return graph_size >= self.get_threshold("memory_efficient")

    def is_large_graph(self, graph_size):
        """Determine if graph is considered large."""
        return graph_size >= self.get_threshold("large_graph")

    def should_force_sequential(self, graph_size):
        """Determine if sequential processing should be forced."""
        return graph_size >= self.get_threshold("sequential_force")

    def get_ultra_fast_generation(self):
        """Get ultra-fast generation setting."""
        return self.current_thresholds["ultra_fast_generation"]

    def record_performance(self, graph_size, algorithm, execution_time, memory_usage):
        """Record performance data for adaptive threshold adjustment."""
        performance_data = {
            "graph_size": graph_size,
            "algorithm": algorithm,
            "execution_time": execution_time,
            "memory_usage": memory_usage,
            "timestamp": time.time()
        }

        self.performance_history.append(performance_data)

        # Keep only recent performance data (last 100 entries)
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

        # Trigger adaptive adjustment if we have enough data
        if len(self.performance_history) >= 10:
            self._adaptive_threshold_adjustment()

    def _adaptive_threshold_adjustment(self):
        """Adjust thresholds based on performance history."""
        try:
            # Analyze recent performance trends
            recent_data = self.performance_history[-20:]  # Last 20 operations

            # Calculate average performance metrics
            avg_time_by_size = {}
            avg_memory_by_size = {}

            for data in recent_data:
                size_bucket = (data["graph_size"] // 100) * 100  # Group by 100s
                if size_bucket not in avg_time_by_size:
                    avg_time_by_size[size_bucket] = []
                    avg_memory_by_size[size_bucket] = []

                avg_time_by_size[size_bucket].append(data["execution_time"])
                avg_memory_by_size[size_bucket].append(data["memory_usage"])

            # Identify performance bottlenecks and adjust thresholds
            for size_bucket, times in avg_time_by_size.items():
                if len(times) >= 3:  # Need at least 3 samples
                    avg_time = sum(times) / len(times)
                    avg_memory = sum(avg_memory_by_size[size_bucket]) / len(avg_memory_by_size[size_bucket])

                    # If performance is poor, increase thresholds (be more conservative)
                    if avg_time > 30.0 or avg_memory > 1000:  # 30 seconds or 1GB
                        self._increase_thresholds(0.1)  # 10% increase
                    # If performance is excellent, decrease thresholds (be more aggressive)
                    elif avg_time < 5.0 and avg_memory < 200:  # 5 seconds and 200MB
                        self._decrease_thresholds(0.05)  # 5% decrease

        except Exception as e:
            logging.warning(f"Adaptive threshold adjustment failed: {e}")

    def _increase_thresholds(self, factor):
        """Increase thresholds to be more conservative."""
        adjustable_thresholds = ["large_graph", "parallel_min", "memory_efficient"]

        for threshold_name in adjustable_thresholds:
            old_value = self.current_thresholds[threshold_name]
            new_value = int(old_value * (1 + factor))
            self.current_thresholds[threshold_name] = new_value

            if threshold_name not in self.threshold_adjustments:
                self.threshold_adjustments[threshold_name] = []
            self.threshold_adjustments[threshold_name].append(("increase", factor, old_value, new_value))

        self._validate_threshold_consistency()
        logging.info(f"Increased thresholds by {factor*100:.1f}% due to performance concerns")

    def _decrease_thresholds(self, factor):
        """Decrease thresholds to be more aggressive."""
        adjustable_thresholds = ["large_graph", "parallel_min", "memory_efficient"]

        for threshold_name in adjustable_thresholds:
            old_value = self.current_thresholds[threshold_name]
            # Don't go below base thresholds
            min_value = self.base_thresholds[threshold_name] // 2
            new_value = max(min_value, int(old_value * (1 - factor)))
            self.current_thresholds[threshold_name] = new_value

            if threshold_name not in self.threshold_adjustments:
                self.threshold_adjustments[threshold_name] = []
            self.threshold_adjustments[threshold_name].append(("decrease", factor, old_value, new_value))

        self._validate_threshold_consistency()
        logging.info(f"Decreased thresholds by {factor*100:.1f}% due to excellent performance")

    def get_current_thresholds(self):
        """Get all current threshold values."""
        return self.current_thresholds.copy()

    def reset_to_defaults(self):
        """Reset thresholds to default values."""
        self.current_thresholds = self.base_thresholds.copy()
        self.performance_history = []
        self.threshold_adjustments = {}
        self._calculate_adaptive_thresholds()
        logging.info("Dynamic thresholds reset to defaults")

# Global instance of dynamic thresholds
_dynamic_thresholds = None

def get_dynamic_thresholds():
    """Get the global dynamic thresholds instance."""
    global _dynamic_thresholds
    if _dynamic_thresholds is None:
        _dynamic_thresholds = DynamicGraphThresholds()
    return _dynamic_thresholds

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

# OPTIMIZATION: Incremental cost calculation class for better performance
class IncrementalCostCalculator:
    """
    Optimized cost calculator that supports incremental updates for edge swaps.
    Avoids full recalculation when only small changes are made to the tree.
    """

    def __init__(self, spanning_tree, max_children, penalty):
        self.max_children = max_children
        self.penalty = penalty
        self.current_cost = None
        self.edge_weights_sum = 0.0
        self.constraint_violations = 0
        self.degrees = {}
        self._update_full_state(spanning_tree)

    def _update_full_state(self, spanning_tree):
        """Update the full state from the spanning tree."""
        # Calculate edge weights sum
        self.edge_weights_sum = sum(data.get('weight', 1) for _, _, data in spanning_tree.edges(data=True))

        # Pre-calculate degrees
        self.degrees = dict(spanning_tree.degree())

        # Calculate constraint violations
        self.constraint_violations = 0
        if self.max_children != float('inf'):
            for node in spanning_tree.nodes():
                node_degree = self.degrees[node]
                children_count = 0

                for neighbor in spanning_tree.neighbors(node):
                    if self.degrees[neighbor] < node_degree:
                        children_count += 1

                if children_count > self.max_children:
                    self.constraint_violations += children_count - self.max_children

        # Calculate total cost
        self.current_cost = self.edge_weights_sum + (self.penalty * self.constraint_violations)

    def get_cost(self):
        """Get the current cost."""
        return self.current_cost

    def calculate_edge_swap_cost_delta(self, spanning_tree, edge_to_remove, edge_to_add, edge_add_weight):
        """
        Calculate the cost delta for an edge swap without full recalculation.
        Returns the cost change (positive = increase, negative = decrease).
        """
        try:
            # Get weight of edge to remove
            edge_remove_weight = spanning_tree.edges[edge_to_remove].get('weight', 1)

            # Weight delta
            weight_delta = edge_add_weight - edge_remove_weight

            # For constraint violations, we need to check the impact
            # This is more complex and might require partial recalculation
            # For now, we'll use a simplified approach

            return weight_delta  # Simplified - only considers weight change

        except Exception:
            # Fallback to full calculation if incremental fails
            return None

    def apply_edge_swap(self, spanning_tree, edge_to_remove, edge_to_add, edge_add_weight):
        """
        Apply an edge swap and update the incremental state.
        """
        try:
            # Calculate delta first
            delta = self.calculate_edge_swap_cost_delta(spanning_tree, edge_to_remove, edge_to_add, edge_add_weight)

            if delta is not None:
                # Apply the change
                self.current_cost += delta

                # Update edge weights sum
                edge_remove_weight = spanning_tree.edges[edge_to_remove].get('weight', 1)
                self.edge_weights_sum += (edge_add_weight - edge_remove_weight)

                # For degrees and violations, we need to recalculate
                # This is still more efficient than full recalculation
                self._update_degrees_and_violations(spanning_tree)

                return True
            else:
                # Fallback to full update
                self._update_full_state(spanning_tree)
                return False

        except Exception:
            # Fallback to full update
            self._update_full_state(spanning_tree)
            return False

    def _update_degrees_and_violations(self, spanning_tree):
        """Update only degrees and constraint violations."""
        # Update degrees
        self.degrees = dict(spanning_tree.degree())

        # Recalculate constraint violations
        old_violations = self.constraint_violations
        self.constraint_violations = 0

        if self.max_children != float('inf'):
            for node in spanning_tree.nodes():
                node_degree = self.degrees[node]
                children_count = 0

                for neighbor in spanning_tree.neighbors(node):
                    if self.degrees[neighbor] < node_degree:
                        children_count += 1

                if children_count > self.max_children:
                    self.constraint_violations += children_count - self.max_children

        # Update total cost
        violation_delta = (self.constraint_violations - old_violations) * self.penalty
        self.current_cost = self.edge_weights_sum + (self.penalty * self.constraint_violations)

# GPU acceleration functions completely removed for system stability
# All cost calculations now use the optimized CPU-only implementation above

#==============================================================================
#                           4.1. FUNZIONI DI PARALLELIZZAZIONE
#==============================================================================

def parallel_cost_evaluation(candidate_solutions, max_children, penalty, cost_function, max_workers=None):
    """
    SIMPLIFIED: Evaluate costs using simple fixed-worker parallelization.

    Educational Implementation:
    - Simple rule: sequential for <5 items, parallel for 5+ items
    - Fixed workers: 2-4 based on CPU cores
    - Basic timeout: 60 seconds
    - Simple fallback to sequential on any error

    Args:
        candidate_solutions: List of spanning trees to evaluate
        max_children: Maximum allowed number of children
        penalty: Penalty for violations
        cost_function: Cost calculation function to use
        max_workers: Ignored (for compatibility) - uses simple worker calculation

    Returns:
        List of costs corresponding to each candidate solution
    """
    # Import simplified parallelization
    from .simple_parallelization import simple_parallel_cost_evaluation

    # Use the simplified implementation
    return simple_parallel_cost_evaluation(candidate_solutions, max_children, penalty, cost_function)

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

        # Apply the edge swap on the copy using safe weight access
        temp_tree.remove_edge(*edge_to_remove)
        # FIXED: Use safe weight access to prevent KeyError
        edge_weight = safe_get_edge_weight(G, edge_to_add[0], edge_to_add[1], default_weight=1)
        temp_tree.add_edge(*edge_to_add, weight=edge_weight)

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
    Evaluate the quality of a solution based on multiple criteria.

    FIXED: Proper implementation that calculates meaningful scores based on:
    - Cost (lower is better)
    - Execution time (lower is better)
    - Memory usage (lower is better)
    - Constraint violations (lower is better)

    Args:
        solution: Dictionary with cost, execution_time, memory, violations
        constraints: Dictionary with max values for normalization

    Returns:
        float: Score where higher values indicate better solutions
    """
    score = 0.0

    # Get solution metrics
    cost = solution.get("cost", float('inf'))
    exec_time = solution.get("execution_time", float('inf'))
    memory = solution.get("memory", float('inf'))
    violations = solution.get("violations", float('inf'))

    # Get reference values for normalization
    max_cost = constraints.get("max_cost", 1.0)
    max_time = constraints.get("max_time", 1.0)
    max_memory = constraints.get("max_memory", 1.0)
    max_violations = constraints.get("max_violations", 1.0)

    # Avoid division by zero
    max_cost = max(max_cost, 1.0)
    max_time = max(max_time, 1.0)
    max_memory = max(max_memory, 1.0)
    max_violations = max(max_violations, 1.0)

    # Calculate normalized scores (inverted so lower values get higher scores)
    # Cost is the most important factor (50% weight)
    cost_score = (1.0 - min(cost / max_cost, 1.0)) * 50.0

    # Violations are critical (30% weight)
    violation_score = (1.0 - min(violations / max_violations, 1.0)) * 30.0

    # Time efficiency (15% weight)
    time_score = (1.0 - min(exec_time / max_time, 1.0)) * 15.0

    # Memory efficiency (5% weight)
    memory_score = (1.0 - min(memory / max_memory, 1.0)) * 5.0

    # Total score
    score = cost_score + violation_score + time_score + memory_score

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

#==============================================================================
#                           UNION-FIND DATA STRUCTURE
#==============================================================================

class UnionFind:
    """
    Union-Find (Disjoint Set Union) data structure with path compression and union by rank.
    Used for efficient cycle detection in graph algorithms.
    """

    def __init__(self, nodes):
        """
        Initialize Union-Find structure.

        Args:
            nodes: Iterable of node identifiers
        """
        self.parent = {node: node for node in nodes}
        self.rank = {node: 0 for node in nodes}
        self.components = len(nodes)

    def find(self, node):
        """
        Find the root of the component containing node with path compression.

        Args:
            node: Node to find root for

        Returns:
            Root node of the component
        """
        if self.parent[node] != node:
            self.parent[node] = self.find(self.parent[node])  # Path compression
        return self.parent[node]

    def union(self, node1, node2):
        """
        Union two components containing node1 and node2.

        Args:
            node1, node2: Nodes to union

        Returns:
            bool: True if union was performed (nodes were in different components)
        """
        root1 = self.find(node1)
        root2 = self.find(node2)

        if root1 == root2:
            return False  # Already in same component

        # Union by rank
        if self.rank[root1] < self.rank[root2]:
            self.parent[root1] = root2
        elif self.rank[root1] > self.rank[root2]:
            self.parent[root2] = root1
        else:
            self.parent[root2] = root1
            self.rank[root1] += 1

        self.components -= 1
        return True

    def connected(self, node1, node2):
        """
        Check if two nodes are in the same component.

        Args:
            node1, node2: Nodes to check

        Returns:
            bool: True if nodes are connected
        """
        return self.find(node1) == self.find(node2)

    def num_components(self):
        """
        Get the number of connected components.

        Returns:
            int: Number of components
        """
        return self.components

#==============================================================================
#                           NEW STANDARDIZED ALGORITHMS
#==============================================================================

def greedy_spanning_tree(G, max_children=float('inf'), penalty=1000):
    """
    Modified Kruskal's algorithm for Degree-Constrained Minimum Spanning Tree (DCMST).

    Implementation Requirements:
    - Sort all edges by increasing weight
    - Initialize Union-Find structure for cycle detection
    - Maintain degree array for each node tracking current degrees
    - For each edge (u,v) in sorted order:
      - If degree[u] < degree_limit[u] AND degree[v] < degree_limit[v]
      - AND u and v are not already connected (check via Union-Find)
      - Then: add edge, update degrees, union components
    - Terminate when you have n-1 edges or exhaust available edges

    Args:
        G: Input graph
        max_children: Maximum degree constraint for each node
        penalty: Penalty for constraint violations

    Returns:
        tuple: (spanning_tree, total_cost)
    """
    global greedy_cost_calls

    if not G or len(G.nodes()) == 0:
        return nx.Graph(), 0

    # Initialize spanning tree
    T = nx.Graph()
    T.add_nodes_from(G.nodes())

    # Sort all edges by weight (ascending)
    edges = []
    for u, v, data in G.edges(data=True):
        weight = data.get('weight', 1)
        edges.append((weight, u, v))
    edges.sort()  # Sort by weight

    # Initialize Union-Find structure
    uf = UnionFind(G.nodes())

    # Initialize degree tracking
    degree = {node: 0 for node in G.nodes()}

    # Set degree limits (handle both uniform and per-node limits)
    if isinstance(max_children, dict):
        degree_limit = max_children
    else:
        degree_limit = {node: max_children for node in G.nodes()}

    edges_added = 0
    target_edges = len(G.nodes()) - 1  # n-1 edges for spanning tree

    # Process edges in order of increasing weight
    for weight, u, v in edges:
        # Check degree constraints
        if degree[u] >= degree_limit.get(u, max_children):
            continue
        if degree[v] >= degree_limit.get(v, max_children):
            continue

        # Check if adding this edge would create a cycle
        if not uf.connected(u, v):
            # Add edge to spanning tree
            T.add_edge(u, v, weight=weight)

            # Update Union-Find structure
            uf.union(u, v)

            # Update degrees
            degree[u] += 1
            degree[v] += 1

            edges_added += 1

            # Check if we have a complete spanning tree
            if edges_added == target_edges:
                break

    # Calculate total cost
    total_cost = calculate_cost_greedy(T, max_children, penalty)

    return T, total_cost

def adaptive_neighborhood_local_search(G, initial_tree, max_children, penalty, max_iterations=5000, stop_event=None, queue=None, callback=None):
    """
    Hill Climbing (First Improvement Local Search) for DCMST.

    Implementation Requirements:
    - Generate initial solution using modified greedy Kruskal
    - Repeat until no improvement found:
      - For each edge in current spanning tree:
        - Remove it temporarily (creating two components)
        - For each edge not in tree that reconnects the two components:
          - If it respects degree constraints AND has lower cost
          - Apply the swap and proceed to next iteration (first improvement)
      - If no swap improves solution: terminate (local optimum reached)

    Args:
        G: Input graph
        initial_tree: Starting tree solution
        max_children: Maximum degree constraint
        penalty: Penalty for constraint violations
        max_iterations: Maximum number of iterations
        stop_event: Threading event to signal termination
        queue: Queue for GUI communication
        callback: Progress callback function

    Returns:
        tuple: (best_tree, cost_calls, score_history)
    """
    global local_search_cost_calls

    if not initial_tree or len(initial_tree.nodes()) == 0:
        # Generate initial solution using greedy algorithm
        initial_tree, _ = greedy_spanning_tree(G, max_children, penalty)

    current_tree = initial_tree.copy()
    best_tree = current_tree.copy()
    best_cost = calculate_cost_local(best_tree, max_children, penalty)

    cost_calls = local_search_cost_calls[0]
    score_history = []
    start_time = time.time()
    iteration = 0

    # Set degree limits
    if isinstance(max_children, dict):
        degree_limit = max_children
    else:
        degree_limit = {node: max_children for node in G.nodes()}

    while iteration < max_iterations:
        if stop_event and stop_event.is_set():
            break

        # Update GUI periodically
        if queue and iteration % 10 == 0:
            queue.put(("iter", f"{iteration}/{max_iterations}"))
            queue.put(("cost", best_cost))

        # Progress callback
        if callback and iteration % 5 == 0:
            message = f"Iteration {iteration}/{max_iterations}"
            callback(message, best_cost, queue=queue, improved=False)

        # Collect data for score history
        if iteration % 5 == 0:
            violations = count_constraint_violations(current_tree, max_children)
            current_time = time.time() - start_time
            current_cost = calculate_cost_local(current_tree, max_children, penalty)

            score_data = {
                "cost": current_cost,
                "execution_time": current_time,
                "memory": 0,
                "violations": violations
            }
            score_history.append((iteration, score_data))

        improvement_found = False

        # Try to improve by swapping edges (first improvement)
        tree_edges = list(current_tree.edges())

        for u, v in tree_edges:
            if improvement_found:
                break

            # Remove edge temporarily
            current_tree.remove_edge(u, v)

            # Find the two components created
            try:
                components = list(nx.connected_components(current_tree))
                if len(components) != 2:
                    # Restore edge and continue
                    weight = safe_get_edge_weight(G, u, v, default_weight=1)
                    current_tree.add_edge(u, v, weight=weight)
                    continue

                comp1, comp2 = components

                # Find edges that can reconnect the components
                for n1 in comp1:
                    if improvement_found:
                        break
                    for n2 in comp2:
                        if improvement_found:
                            break

                        # Skip the original edge
                        if (n1, n2) == (u, v) or (n2, n1) == (u, v):
                            continue

                        # Check if this edge exists in the original graph
                        if not G.has_edge(n1, n2):
                            continue

                        # Check degree constraints
                        current_degree_n1 = current_tree.degree(n1)
                        current_degree_n2 = current_tree.degree(n2)

                        if current_degree_n1 >= degree_limit.get(n1, max_children):
                            continue
                        if current_degree_n2 >= degree_limit.get(n2, max_children):
                            continue

                        # Add the new edge temporarily
                        weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
                        current_tree.add_edge(n1, n2, weight=weight)

                        # Calculate new cost
                        new_cost = calculate_cost_local(current_tree, max_children, penalty)
                        cost_calls += 1

                        # Check if this is an improvement
                        if new_cost < best_cost:
                            # First improvement found - accept it
                            best_tree = current_tree.copy()
                            best_cost = new_cost
                            improvement_found = True

                            if callback:
                                callback(iteration, best_cost, queue=queue, improved=True)
                            break
                        else:
                            # Remove the test edge
                            current_tree.remove_edge(n1, n2)

                # If no improvement found, restore the original edge
                if not improvement_found:
                    weight = safe_get_edge_weight(G, u, v, default_weight=1)
                    current_tree.add_edge(u, v, weight=weight)

            except Exception as e:
                # Restore edge on error
                if not current_tree.has_edge(u, v):
                    weight = safe_get_edge_weight(G, u, v, default_weight=1)
                    current_tree.add_edge(u, v, weight=weight)
                logging.warning(f"Error in hill climbing: {e}")

        # If no improvement found, we've reached a local optimum
        if not improvement_found:
            if queue:
                queue.put(("log", (f"Hill Climbing terminated: local optimum reached at iteration {iteration}", "info")))
            break

        iteration += 1

    # Final report
    if queue:
        queue.put(("log", (f"Hill Climbing completed: {iteration+1} iterations, {cost_calls} cost function calls", "info")))

    local_search_cost_calls[0] = cost_calls

    return best_tree, cost_calls, score_history

def simulated_annealing_spanning_tree(G, max_children=3, penalty=1000, max_iterations=10000, initial_temperature=200, cooling_rate=0.98, stop_event=None, queue=None, return_stats=False, initial_tree=None, progress_callback=None, greedy_tree=None):
    """
    Simulated Annealing algorithm for DCMST.

    Implementation Requirements:
    - Generate initial solution using greedy algorithm
    - Set initial temperature T (e.g., 100), cooling factor α (e.g., 0.95)
    - While T > minimum_threshold:
      - For fixed_number_iterations at current temperature:
        - Generate neighbor using random edge swap
        - If neighbor is valid: calculate cost difference Δ
        - If Δ < 0 OR random() < exp(-Δ/T): accept the move
      - Reduce temperature: T = T × α
    - Return best solution found during entire process

    Args:
        G: Input graph
        max_children: Maximum degree constraint
        penalty: Penalty for constraint violations
        max_iterations: Maximum number of iterations
        initial_temperature: Starting temperature
        cooling_rate: Temperature reduction factor
        stop_event: Threading event to signal termination
        queue: Queue for GUI communication
        return_stats: Whether to return detailed statistics
        initial_tree: Initial tree solution
        progress_callback: Progress callback function
        greedy_tree: Greedy solution for comparison

    Returns:
        tuple: Depending on return_stats, either (tree, cost, iterations, accepted, score_history)
               or (tree, stats, score_history)
    """
    global sa_cost_calls

    # Choose best starting solution
    if initial_tree is not None and greedy_tree is not None:
        initial_cost = calculate_cost_sa(initial_tree, max_children, penalty)
        greedy_cost = calculate_cost_sa(greedy_tree, max_children, penalty)

        if initial_cost <= greedy_cost:
            current_tree = initial_tree.copy()
            if queue:
                queue.put(("log", (f"SA starting from Local Search solution (cost: {initial_cost:.2f})", "info")))
        else:
            current_tree = greedy_tree.copy()
            if queue:
                queue.put(("log", (f"SA starting from Greedy solution (cost: {greedy_cost:.2f})", "info")))
    elif initial_tree is not None:
        current_tree = initial_tree.copy()
        if queue:
            queue.put(("log", ("SA starting from provided initial solution", "info")))
    elif greedy_tree is not None:
        current_tree = greedy_tree.copy()
        if queue:
            queue.put(("log", ("SA starting from provided greedy solution", "info")))
    else:
        # Generate new greedy solution
        current_tree, _ = greedy_spanning_tree(G, max_children, penalty)
        if queue:
            queue.put(("log", ("SA starting from newly generated greedy solution", "info")))

    # Initialize SA parameters
    current_cost = calculate_cost_sa(current_tree, max_children, penalty)
    best_tree = current_tree.copy()
    best_cost = current_cost

    temperature = initial_temperature
    min_temperature = 0.01
    iteration = 0
    accepted_count = 0
    rejected_count = 0

    cost_calls = sa_cost_calls[0]
    score_history = []
    start_time = time.time()

    # Set degree limits
    if isinstance(max_children, dict):
        degree_limit = max_children
    else:
        degree_limit = {node: max_children for node in G.nodes()}

    if queue:
        queue.put(("log", (f"SA started: T={temperature:.2f}, iterations={max_iterations}, cooling={cooling_rate:.3f}", "info")))

    while temperature > min_temperature and iteration < max_iterations:
        if stop_event and stop_event.is_set():
            break

        # Update GUI periodically
        if queue and iteration % max(1, max_iterations // 100) == 0:
            progress_pct = min(100, (iteration / max_iterations) * 100)
            queue.put(("progress", progress_pct))
            queue.put(("temp", f"{temperature:.6f}"))
            queue.put(("iter", f"{iteration}/{max_iterations}"))
            queue.put(("cost", f"{current_cost}"))

        # Collect data for score history
        if iteration % max(1, max_iterations // 100) == 0:
            violations = count_constraint_violations(current_tree, max_children)
            current_time = time.time() - start_time

            score_data = {
                "cost": current_cost,
                "execution_time": current_time,
                "memory": 0,
                "violations": violations
            }
            score_history.append((iteration, score_data))

        # Generate neighbor using edge swap
        neighbor_tree = current_tree.copy()
        neighbor_cost = _generate_neighbor_with_edge_swap(G, neighbor_tree, max_children, penalty, degree_limit)

        if neighbor_cost is not None:
            cost_calls += 1

            # Calculate cost difference
            delta_cost = neighbor_cost - current_cost

            # Accept or reject the neighbor
            if delta_cost <= 0:
                # Always accept improvements
                current_tree = neighbor_tree
                current_cost = neighbor_cost
                accepted_count += 1

                # Update best solution if this is better
                if current_cost < best_cost:
                    best_tree = current_tree.copy()
                    best_cost = current_cost

                    if progress_callback:
                        progress_callback(iteration, temperature, current_cost, True, max_iterations)
            else:
                # Accept worse solution with probability exp(-Δ/T)
                acceptance_prob = math.exp(-delta_cost / temperature)
                if random.random() < acceptance_prob:
                    current_tree = neighbor_tree
                    current_cost = neighbor_cost
                    accepted_count += 1

                    if progress_callback:
                        progress_callback(iteration, temperature, current_cost, True, max_iterations)
                else:
                    rejected_count += 1

                    if progress_callback:
                        progress_callback(iteration, temperature, current_cost, False, max_iterations)
        else:
            rejected_count += 1

        # Cool down temperature
        temperature *= cooling_rate
        iteration += 1

    # Final report
    if queue:
        final_violations = count_constraint_violations(best_tree, max_children)
        acceptance_rate = accepted_count / (accepted_count + rejected_count) if (accepted_count + rejected_count) > 0 else 0
        queue.put(("log", (f"SA completed: cost={best_cost:.2f}, iterations={iteration}, accepted={accepted_count}, violations={final_violations}", "success")))
        queue.put(("log", (f"SA stats: acceptance_rate={acceptance_rate:.1%}, final_temp={temperature:.6f}", "info")))

    sa_cost_calls[0] = cost_calls

    # Return appropriate format based on return_stats flag
    if return_stats:
        stats = {
            "final_cost": best_cost,
            "iterations": iteration,
            "accepted_moves": accepted_count,
            "rejected_moves": rejected_count,
            "final_temperature": temperature,
            "acceptance_rate": accepted_count / (accepted_count + rejected_count) if (accepted_count + rejected_count) > 0 else 0
        }
        return best_tree, stats, score_history
    else:
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
                weight = safe_get_edge_weight(G, u, v, default_weight=1)
                tree.add_edge(u, v, weight=weight)
            return generate_neighbor_tree(G, tree, max_children, penalty)

        # Find a new edge to connect the components
        component1 = components[0]
        component2 = components[1]
    except (KeyError, nx.NetworkXError) as e:
        logging.debug(f"Error during neighbor generation: {e}")
        # Try to restore the original edge if possible
        if G.has_edge(u, v):
            weight = safe_get_edge_weight(G, u, v, default_weight=1)
            tree.add_edge(u, v, weight=weight)
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
                base_weight = safe_get_edge_weight(G, node1, node2, default_weight=1)
                effective_weight = base_weight + (child_penalty * penalty * 0.1)

                potential_edges.append((node1, node2, effective_weight))

    # If no potential edges found, revert and try again
    if not potential_edges:
        weight = safe_get_edge_weight(G, u, v, default_weight=1)
        tree.add_edge(u, v, weight=weight)
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
    weight = safe_get_edge_weight(G, node1, node2, default_weight=1)
    tree.add_edge(node1, node2, weight=weight)

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
        edges = [(node, neighbor, safe_get_edge_weight(tree, node, neighbor, default_weight=1))
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
                            weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
                            alt_edges.append((n1, n2, weight))

                if alt_edges:
                    # Sort by weight
                    alt_edges.sort(key=lambda x: x[2])

                    # Pick one of the best alternatives with some randomness
                    idx = min(int(random.expovariate(1) * len(alt_edges)), len(alt_edges) - 1)
                    n1, n2, _ = alt_edges[idx]
                    weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
                    tree.add_edge(n1, n2, weight=weight)
                    return tree  # Successfully modified
                else:
                    # No alternative found, put back the original edge
                    weight = safe_get_edge_weight(G, u, v, default_weight=1)
                    tree.add_edge(u, v, weight=weight)

    # If we get here, either there are no constraint violations or we couldn't fix them
    # Try a standard edge swap but with more focus on high-cost edges

    # Find high-cost edges in the tree
    edges = [(u, v, safe_get_edge_weight(tree, u, v, default_weight=1)) for u, v in tree.edges()]
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
        weight = safe_get_edge_weight(G, u, v, default_weight=1)
        tree.add_edge(u, v, weight=weight)
        return generate_neighbor_tree(G, tree, max_children, penalty)

    # Find a new edge to connect components
    comp1, comp2 = components[0], components[1]

    potential_edges = []
    for n1 in comp1:
        for n2 in comp2:
            if G.has_edge(n1, n2) and (n1, n2) != (u, v):
                weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
                potential_edges.append((n1, n2, weight))

    if not potential_edges:
        weight = safe_get_edge_weight(G, u, v, default_weight=1)
        tree.add_edge(u, v, weight=weight)
        return generate_neighbor_tree(G, tree, max_children, penalty)

    # Sort by weight
    potential_edges.sort(key=lambda x: x[2])

    # Pick from the better edges with some randomness
    # More likely to pick better edges, but still some exploration
    idx = min(int(random.expovariate(2) * len(potential_edges)), len(potential_edges) - 1)
    n1, n2, _ = potential_edges[idx]

    # Add the new edge
    weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
    tree.add_edge(n1, n2, weight=weight)

    return tree

# Placeholder for helper functions
#==============================================================================
#                           HELPER FUNCTIONS FOR NEW ALGORITHMS
#==============================================================================

def _generate_neighbor_with_edge_swap(G, tree, max_children, penalty, degree_limit):
    """
    Generate a neighbor solution by performing an edge swap.

    Common Operator: Edge-swap (remove edge + add edge that maintains connectivity and degree constraints)

    Args:
        G: Original graph
        tree: Current tree to modify
        max_children: Maximum degree constraint
        penalty: Penalty for violations
        degree_limit: Dictionary of degree limits per node

    Returns:
        float or None: Cost of the neighbor tree, or None if no valid neighbor found
    """
    tree_edges = list(tree.edges())
    if not tree_edges:
        return None

    # Select a random edge to remove
    edge_to_remove = random.choice(tree_edges)
    u, v = edge_to_remove

    # Remove the edge
    tree.remove_edge(u, v)

    try:
        # Find the two components created
        components = list(nx.connected_components(tree))
        if len(components) != 2:
            # Restore edge and return None
            weight = safe_get_edge_weight(G, u, v, default_weight=1)
            tree.add_edge(u, v, weight=weight)
            return None

        comp1, comp2 = components

        # Find edges that can reconnect the components
        candidate_edges = []
        for n1 in comp1:
            for n2 in comp2:
                if G.has_edge(n1, n2) and (n1, n2) != (u, v) and (n2, n1) != (u, v):
                    # Check degree constraints
                    current_degree_n1 = tree.degree(n1)
                    current_degree_n2 = tree.degree(n2)

                    if (current_degree_n1 < degree_limit.get(n1, max_children) and
                        current_degree_n2 < degree_limit.get(n2, max_children)):
                        candidate_edges.append((n1, n2))

        if not candidate_edges:
            # No valid reconnecting edges, restore original
            weight = safe_get_edge_weight(G, u, v, default_weight=1)
            tree.add_edge(u, v, weight=weight)
            return None

        # Select a random reconnecting edge
        new_edge = random.choice(candidate_edges)
        n1, n2 = new_edge

        # Add the new edge
        weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
        tree.add_edge(n1, n2, weight=weight)

        # Calculate and return the cost
        return calculate_cost_sa(tree, max_children, penalty)

    except Exception as e:
        # Restore original edge on error
        if not tree.has_edge(u, v):
            weight = safe_get_edge_weight(G, u, v, default_weight=1)
            tree.add_edge(u, v, weight=weight)
        logging.warning(f"Error in neighbor generation: {e}")
        return None

def get_violating_nodes(tree, max_children):
    """
    Get nodes that violate the degree constraints.

    Args:
        tree: Spanning tree
        max_children: Maximum degree constraint (can be dict or int)

    Returns:
        list: Nodes that violate degree constraints
    """
    violating_nodes = []

    if isinstance(max_children, dict):
        degree_limit = max_children
    else:
        degree_limit = {node: max_children for node in tree.nodes()}

    for node in tree.nodes():
        current_degree = tree.degree(node)
        limit = degree_limit.get(node, max_children)

        if current_degree > limit:
            violating_nodes.append(node)

    return violating_nodes

def try_random_edge_swap(G, current_tree, max_children, penalty, neighborhood_size=1):
    """
    Try random edge swaps to improve the current tree.

    Args:
        G: Original graph
        current_tree: Current spanning tree (modified in-place)
        max_children: Maximum degree constraint
        penalty: Penalty for violations
        neighborhood_size: Number of swaps to try

    Returns:
        bool: True if improvement was made
    """
    if isinstance(max_children, dict):
        degree_limit = max_children
    else:
        degree_limit = {node: max_children for node in G.nodes()}

    best_cost = calculate_cost_local(current_tree, max_children, penalty)
    best_tree = None

    for _ in range(neighborhood_size):
        # Create a copy to test
        test_tree = current_tree.copy()

        # Try to generate a neighbor
        new_cost = _generate_neighbor_with_edge_swap(G, test_tree, max_children, penalty, degree_limit)

        if new_cost is not None and new_cost < best_cost:
            best_cost = new_cost
            best_tree = test_tree.copy()

    # Apply the best improvement if found
    if best_tree is not None:
        current_tree.clear()
        current_tree.add_edges_from(best_tree.edges(data=True))
        return True

    return False

def fix_constraint_violations(G, current_tree, constrained_nodes, max_children, penalty, neighborhood_size=1):
    """
    Try to fix constraint violations by swapping edges.

    Args:
        G: Original graph
        current_tree: Current spanning tree (modified in-place)
        constrained_nodes: List of nodes violating constraints
        max_children: Maximum degree constraint
        penalty: Penalty for violations
        neighborhood_size: Number of attempts per node

    Returns:
        bool: True if improvement was made
    """
    if not constrained_nodes:
        return False

    if isinstance(max_children, dict):
        degree_limit = max_children
    else:
        degree_limit = {node: max_children for node in G.nodes()}

    best_cost = calculate_cost_local(current_tree, max_children, penalty)
    best_tree = None

    for node in constrained_nodes:
        for _ in range(neighborhood_size):
            # Create a copy to test
            test_tree = current_tree.copy()

            # Try to reduce degree of this node by swapping one of its edges
            neighbors = list(test_tree.neighbors(node))
            if not neighbors:
                continue

            # Select an edge to remove from the violating node
            neighbor_to_remove = random.choice(neighbors)
            test_tree.remove_edge(node, neighbor_to_remove)

            try:
                # Find components
                components = list(nx.connected_components(test_tree))
                if len(components) != 2:
                    continue

                comp1, comp2 = components

                # Find alternative edges that don't involve the violating node
                alternative_edges = []
                for n1 in comp1:
                    if n1 == node:
                        continue
                    for n2 in comp2:
                        if n2 == node:
                            continue
                        if G.has_edge(n1, n2):
                            # Check degree constraints
                            if (test_tree.degree(n1) < degree_limit.get(n1, max_children) and
                                test_tree.degree(n2) < degree_limit.get(n2, max_children)):
                                alternative_edges.append((n1, n2))

                if alternative_edges:
                    # Select a random alternative
                    n1, n2 = random.choice(alternative_edges)
                    weight = safe_get_edge_weight(G, n1, n2, default_weight=1)
                    test_tree.add_edge(n1, n2, weight=weight)

                    # Calculate new cost
                    new_cost = calculate_cost_local(test_tree, max_children, penalty)

                    if new_cost < best_cost:
                        best_cost = new_cost
                        best_tree = test_tree.copy()

            except Exception as e:
                logging.warning(f"Error in constraint violation fix: {e}")
                continue

    # Apply the best improvement if found
    if best_tree is not None:
        current_tree.clear()
        current_tree.add_edges_from(best_tree.edges(data=True))
        return True

    return False


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
        # Execute standard greedy algorithm with safety wrapper and adaptive timeout
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

    # Record performance for dynamic threshold adjustment
    dynamic_thresholds = get_dynamic_thresholds()
    dynamic_thresholds.record_performance(len(G.nodes()), "greedy", greedy_time, greedy_memory)

    # Record performance in enhanced tracker
    performance_tracker = get_performance_tracker()
    performance_tracker.record_algorithm_run(
        algorithm_name="Greedy",
        graph_size=len(G.nodes()),
        execution_time=greedy_time,
        memory_usage=greedy_memory,
        cost=greedy_cost,
        violations=greedy_violations,
        metadata={"cost_calls": greedy_cost_calls[0], "instance": instance_name}
    )

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

    # Record performance for dynamic threshold adjustment
    dynamic_thresholds = get_dynamic_thresholds()
    dynamic_thresholds.record_performance(len(G.nodes()), "local_search", local_time, local_memory)

    # Record performance in enhanced tracker
    performance_tracker = get_performance_tracker()
    performance_tracker.record_algorithm_run(
        algorithm_name="Local Search",
        graph_size=len(G.nodes()),
        execution_time=local_time,
        memory_usage=local_memory,
        cost=local_cost,
        violations=local_violations,
        metadata={"cost_calls": local_search_cost_calls[0], "instance": instance_name}
    )

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

            # ENHANCEMENT: Pass both local_tree and greedy_tree to SA for optimal starting solution
            sa_tree, sa_cost, sa_iterations, sa_accepts, sa_score_history = safe_execution_wrapper(
                simulated_annealing_spanning_tree,
                G, max_children, penalty,
                initial_tree=local_tree,  # Local search result (primary choice)
                greedy_tree=greedy_tree,  # Greedy result (backup choice)
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

    # Record performance for dynamic threshold adjustment
    dynamic_thresholds = get_dynamic_thresholds()
    dynamic_thresholds.record_performance(len(G.nodes()), "simulated_annealing", sa_time, sa_memory)

    # Record performance in enhanced tracker
    performance_tracker = get_performance_tracker()
    performance_tracker.record_algorithm_run(
        algorithm_name="Simulated Annealing",
        graph_size=len(G.nodes()),
        execution_time=sa_time,
        memory_usage=sa_memory,
        cost=sa_cost,
        violations=sa_violations,
        metadata={"cost_calls": sa_cost_calls[0], "iterations": sa_iterations, "instance": instance_name}
    )

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



def _enhanced_local_search_worker(G, initial_tree, max_degree, penalty, worker_id, stop_event, queue):
    """
    Enhanced worker function for parallel local search with better monitoring and communication.

    Args:
        G: NetworkX graph
        initial_tree: Initial spanning tree solution
        max_degree: Maximum degree constraint
        penalty: Penalty for constraint violations
        worker_id: Unique identifier for this worker
        stop_event: Threading event for early termination
        queue: Communication queue (not used in worker to avoid conflicts)

    Returns:
        tuple: (worker_id, best_tree, total_calls, score_history, execution_time)
    """
    start_time = time.time()

    try:
        # CRITICAL FIX: Validate and fix graph weights before starting
        is_valid, num_fixed, errors = validate_graph_weights(G, fix_missing=True)
        if num_fixed > 0:
            logging.debug(f"Worker {worker_id}: Fixed {num_fixed} missing weights")

        # Set unique random seed for diversity
        random.seed(hash((worker_id, time.time())) % 2**32)
        np.random.seed(hash((worker_id, time.time())) % 2**32)

        # Execute local search with stop event monitoring
        tree, calls, score_history = adaptive_neighborhood_local_search(
            G, initial_tree.copy(), max_degree, penalty,
            stop_event=stop_event, queue=None  # Don't pass queue to avoid conflicts
        )

        execution_time = time.time() - start_time
        return worker_id, tree, calls, score_history, execution_time

    except Exception as e:
        logging.warning(f"Enhanced local search worker {worker_id} failed: {e}")
        execution_time = time.time() - start_time
        # Return initial tree as fallback
        return worker_id, initial_tree.copy(), 0, [], execution_time

def _create_perturbed_solution(G, initial_tree, max_degree, perturbation_level=0.1):
    """
    Create a perturbed version of the initial solution to provide diversity for parallel workers.

    Args:
        G: NetworkX graph
        initial_tree: Initial spanning tree
        max_degree: Maximum degree constraint
        perturbation_level: Level of perturbation (0.0 to 1.0)

    Returns:
        NetworkX graph: Perturbed spanning tree
    """
    try:
        perturbed_tree = initial_tree.copy()
        num_edges = len(perturbed_tree.edges())
        num_perturbations = max(1, int(num_edges * perturbation_level))

        # Get all possible edges from the original graph
        all_edges = list(G.edges())
        tree_edges = set(perturbed_tree.edges())

        for _ in range(num_perturbations):
            # Try to make a small modification
            if len(tree_edges) > 1:
                # Remove a random edge
                edge_to_remove = random.choice(list(tree_edges))
                perturbed_tree.remove_edge(*edge_to_remove)
                tree_edges.remove(edge_to_remove)

                # Add a random edge that maintains connectivity
                possible_edges = [e for e in all_edges if e not in tree_edges]
                if possible_edges:
                    edge_to_add = random.choice(possible_edges)
                    perturbed_tree.add_edge(*edge_to_add)
                    tree_edges.add(edge_to_add)

                    # Check if still connected and is a tree
                    if not nx.is_connected(perturbed_tree) or len(perturbed_tree.edges()) != len(G.nodes()) - 1:
                        # Revert if not valid
                        perturbed_tree.remove_edge(*edge_to_add)
                        perturbed_tree.add_edge(*edge_to_remove)
                        tree_edges.remove(edge_to_add)
                        tree_edges.add(edge_to_remove)

        return perturbed_tree

    except Exception as e:
        logging.warning(f"Failed to create perturbed solution: {e}")
        return initial_tree.copy()

def parallel_local_search(G, initial_tree, max_degree, penalty, num_threads=None, stop_event=None, queue=None):
    """
    SIMPLIFIED: Parallel local search with simple fixed-worker approach.

    Educational Implementation:
    - Simple rule: sequential for small graphs (<20 nodes), parallel for larger ones
    - Fixed workers: 2-4 based on CPU cores
    - Basic timeout: 60 seconds
    - Simple fallback to sequential on any error

    Args:
        G: NetworkX graph
        initial_tree: Initial spanning tree solution
        max_degree: Maximum degree constraint
        penalty: Penalty for constraint violations
        num_threads: Ignored (for compatibility) - uses simple worker calculation
        stop_event: Threading event for early termination
        queue: Communication queue for progress updates

    Returns:
        tuple: (best_tree, total_cost_calls, best_score_history)
    """
    # Import simplified parallelization
    from .simple_parallelization import simple_parallel_local_search

    # Use the simplified implementation
    return simple_parallel_local_search(G, initial_tree, max_degree, penalty, stop_event, queue)



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
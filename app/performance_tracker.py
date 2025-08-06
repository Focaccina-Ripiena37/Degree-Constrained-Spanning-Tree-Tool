#!/usr/bin/env python3
"""
Enhanced Performance Tracking System for DCST Tool.
Provides comprehensive metrics collection, analysis, and visualization.
"""

import time
import threading
import logging
import json
import os
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import statistics

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - system metrics will be limited")

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not available - performance plots will be disabled")


class PerformanceMetrics:
    """Container for performance metrics with statistical analysis."""
    
    def __init__(self, name: str, max_history: int = 1000):
        self.name = name
        self.max_history = max_history
        self.values = deque(maxlen=max_history)
        self.timestamps = deque(maxlen=max_history)
        self.metadata = deque(maxlen=max_history)
        self._lock = threading.Lock()
    
    def add_measurement(self, value: float, metadata: Dict[str, Any] = None):
        """Add a new measurement with timestamp and optional metadata."""
        with self._lock:
            self.values.append(value)
            self.timestamps.append(time.time())
            self.metadata.append(metadata or {})
    
    def get_statistics(self) -> Dict[str, float]:
        """Calculate comprehensive statistics for the metric."""
        with self._lock:
            if not self.values:
                return {}
            
            values_list = list(self.values)
            return {
                'count': len(values_list),
                'mean': statistics.mean(values_list),
                'median': statistics.median(values_list),
                'min': min(values_list),
                'max': max(values_list),
                'std_dev': statistics.stdev(values_list) if len(values_list) > 1 else 0.0,
                'latest': values_list[-1],
                'trend': self._calculate_trend()
            }
    
    def _calculate_trend(self) -> str:
        """Calculate trend direction based on recent measurements."""
        if len(self.values) < 5:
            return "insufficient_data"
        
        recent_values = list(self.values)[-5:]
        first_half = statistics.mean(recent_values[:2])
        second_half = statistics.mean(recent_values[-2:])
        
        if second_half > first_half * 1.1:
            return "increasing"
        elif second_half < first_half * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def get_recent_values(self, count: int = 10) -> List[Tuple[float, float]]:
        """Get recent values with timestamps."""
        with self._lock:
            if not self.values:
                return []
            
            recent_count = min(count, len(self.values))
            return list(zip(
                list(self.timestamps)[-recent_count:],
                list(self.values)[-recent_count:]
            ))


class EnhancedPerformanceTracker:
    """Enhanced performance tracking system with comprehensive metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.session_start = time.time()
        self.algorithm_runs = defaultdict(list)
        self.system_metrics = PerformanceMetrics("system", max_history=500)
        self._lock = threading.Lock()
        self._monitoring_active = False
        self._monitor_thread = None
        
        # Initialize core metrics
        self._initialize_core_metrics()
        
        # Start system monitoring if psutil is available
        if PSUTIL_AVAILABLE:
            self.start_system_monitoring()
    
    def _initialize_core_metrics(self):
        """Initialize core performance metrics."""
        core_metrics = [
            "algorithm_execution_time",
            "algorithm_memory_usage",
            "graph_generation_time",
            "visualization_time",
            "cost_evaluation_calls",
            "constraint_violations",
            "solution_quality"
        ]
        
        for metric_name in core_metrics:
            self.metrics[metric_name] = PerformanceMetrics(metric_name)
    
    def start_system_monitoring(self):
        """Start background system monitoring."""
        if not PSUTIL_AVAILABLE or self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            daemon=True,
            name="SystemMonitor"
        )
        self._monitor_thread.start()
        logging.info("System monitoring started")
    
    def stop_system_monitoring(self):
        """Stop background system monitoring."""
        self._monitoring_active = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        logging.info("System monitoring stopped")
    
    def _system_monitor_loop(self):
        """Background loop for system monitoring."""
        while self._monitoring_active:
            try:
                if PSUTIL_AVAILABLE:
                    # Collect system metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    
                    self.record_metric("system_cpu_usage", cpu_percent, {
                        "timestamp": time.time(),
                        "type": "system"
                    })
                    
                    self.record_metric("system_memory_usage", memory.percent, {
                        "available_gb": memory.available / (1024**3),
                        "used_gb": memory.used / (1024**3),
                        "timestamp": time.time(),
                        "type": "system"
                    })
                
                time.sleep(5)  # Monitor every 5 seconds
            except Exception as e:
                logging.warning(f"System monitoring error: {e}")
                time.sleep(10)  # Wait longer on error
    
    def record_metric(self, metric_name: str, value: float, metadata: Dict[str, Any] = None):
        """Record a performance metric."""
        with self._lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = PerformanceMetrics(metric_name)
            
            self.metrics[metric_name].add_measurement(value, metadata)
    
    def record_algorithm_run(self, algorithm_name: str, graph_size: int, 
                           execution_time: float, memory_usage: float,
                           cost: float, violations: int, metadata: Dict[str, Any] = None):
        """Record a complete algorithm run with all metrics."""
        run_data = {
            "algorithm": algorithm_name,
            "graph_size": graph_size,
            "execution_time": execution_time,
            "memory_usage": memory_usage,
            "cost": cost,
            "violations": violations,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        with self._lock:
            self.algorithm_runs[algorithm_name].append(run_data)
        
        # Record individual metrics
        self.record_metric("algorithm_execution_time", execution_time, {
            "algorithm": algorithm_name,
            "graph_size": graph_size
        })
        
        self.record_metric("algorithm_memory_usage", memory_usage, {
            "algorithm": algorithm_name,
            "graph_size": graph_size
        })
        
        self.record_metric("solution_quality", cost, {
            "algorithm": algorithm_name,
            "graph_size": graph_size,
            "violations": violations
        })
        
        self.record_metric("constraint_violations", violations, {
            "algorithm": algorithm_name,
            "graph_size": graph_size
        })
    
    def get_algorithm_performance_summary(self, algorithm_name: str = None) -> Dict[str, Any]:
        """Get performance summary for algorithms."""
        with self._lock:
            if algorithm_name:
                runs = self.algorithm_runs.get(algorithm_name, [])
                if not runs:
                    return {}
                
                return self._calculate_algorithm_summary(algorithm_name, runs)
            else:
                summary = {}
                for algo_name, runs in self.algorithm_runs.items():
                    if runs:
                        summary[algo_name] = self._calculate_algorithm_summary(algo_name, runs)
                return summary
    
    def _calculate_algorithm_summary(self, algorithm_name: str, runs: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics for an algorithm."""
        if not runs:
            return {}
        
        execution_times = [run["execution_time"] for run in runs]
        memory_usages = [run["memory_usage"] for run in runs]
        costs = [run["cost"] for run in runs]
        violations = [run["violations"] for run in runs]
        
        return {
            "total_runs": len(runs),
            "execution_time": {
                "mean": statistics.mean(execution_times),
                "median": statistics.median(execution_times),
                "min": min(execution_times),
                "max": max(execution_times),
                "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
            },
            "memory_usage": {
                "mean": statistics.mean(memory_usages),
                "median": statistics.median(memory_usages),
                "min": min(memory_usages),
                "max": max(memory_usages)
            },
            "solution_quality": {
                "best_cost": min(costs),
                "worst_cost": max(costs),
                "mean_cost": statistics.mean(costs),
                "total_violations": sum(violations),
                "violation_rate": sum(1 for v in violations if v > 0) / len(violations)
            },
            "latest_run": runs[-1]
        }
    
    def get_metric_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a specific metric."""
        with self._lock:
            if metric_name in self.metrics:
                return self.metrics[metric_name].get_statistics()
            return {}
    
    def export_performance_data(self, filename: str = None) -> str:
        """Export performance data to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_data_{timestamp}.json"
        
        export_data = {
            "session_info": {
                "start_time": self.session_start,
                "export_time": time.time(),
                "duration_seconds": time.time() - self.session_start
            },
            "algorithm_runs": dict(self.algorithm_runs),
            "metric_summaries": {
                name: metric.get_statistics()
                for name, metric in self.metrics.items()
            }
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            logging.info(f"Performance data exported to {filename}")
            return filename
        except Exception as e:
            logging.error(f"Failed to export performance data: {e}")
            raise
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report."""
        report_lines = [
            "DCST Tool - Performance Report",
            "=" * 50,
            f"Session Duration: {time.time() - self.session_start:.2f} seconds",
            f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Algorithm performance summary
        algo_summary = self.get_algorithm_performance_summary()
        if algo_summary:
            report_lines.append("Algorithm Performance Summary:")
            report_lines.append("-" * 30)
            
            for algo_name, stats in algo_summary.items():
                report_lines.extend([
                    f"\n{algo_name}:",
                    f"  Total Runs: {stats['total_runs']}",
                    f"  Avg Execution Time: {stats['execution_time']['mean']:.3f}s",
                    f"  Avg Memory Usage: {stats['memory_usage']['mean']:.1f}KB",
                    f"  Best Solution Cost: {stats['solution_quality']['best_cost']}",
                    f"  Violation Rate: {stats['solution_quality']['violation_rate']:.1%}"
                ])
        
        # System metrics summary
        if PSUTIL_AVAILABLE:
            cpu_stats = self.get_metric_statistics("system_cpu_usage")
            memory_stats = self.get_metric_statistics("system_memory_usage")
            
            if cpu_stats or memory_stats:
                report_lines.extend([
                    "\n\nSystem Performance:",
                    "-" * 20
                ])
                
                if cpu_stats:
                    report_lines.append(f"CPU Usage - Avg: {cpu_stats.get('mean', 0):.1f}%, Peak: {cpu_stats.get('max', 0):.1f}%")
                
                if memory_stats:
                    report_lines.append(f"Memory Usage - Avg: {memory_stats.get('mean', 0):.1f}%, Peak: {memory_stats.get('max', 0):.1f}%")
        
        return "\n".join(report_lines)


# Global performance tracker instance
_performance_tracker = None
_tracker_lock = threading.Lock()


def get_performance_tracker() -> EnhancedPerformanceTracker:
    """Get the global performance tracker instance."""
    global _performance_tracker
    with _tracker_lock:
        if _performance_tracker is None:
            _performance_tracker = EnhancedPerformanceTracker()
        return _performance_tracker


def cleanup_performance_tracker():
    """Cleanup the global performance tracker."""
    global _performance_tracker
    with _tracker_lock:
        if _performance_tracker:
            _performance_tracker.stop_system_monitoring()
            _performance_tracker = None

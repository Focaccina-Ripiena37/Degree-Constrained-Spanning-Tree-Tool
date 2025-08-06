#!/usr/bin/env python3
"""
Enhanced Visualization Module for DCST Tool.
Provides improved plotting capabilities and result visualization.
"""

import os
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.colors import LinearSegmentedColormap
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
    
    # Set style for better-looking plots
    plt.style.use('default')
    sns.set_palette("husl")
    
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib/seaborn not available - enhanced visualization disabled")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available - some visualization features disabled")

from .config import (
    ALGORITHM_COLORS, GRAPH_FIGURE_SIZE, TABLE_FIGURE_SIZE, 
    EVOLUTION_FIGURE_SIZE, IMAGE_DPI, TABLE_IMAGE_DPI
)


class EnhancedVisualization:
    """Enhanced visualization system with improved plotting capabilities."""
    
    def __init__(self):
        self.color_schemes = {
            'algorithms': ALGORITHM_COLORS,
            'performance': {
                'excellent': '#2ECC71',
                'good': '#3498DB', 
                'average': '#F39C12',
                'poor': '#E74C3C',
                'critical': '#8E44AD'
            },
            'metrics': {
                'time': '#3498DB',
                'memory': '#E74C3C',
                'cost': '#2ECC71',
                'violations': '#F39C12'
            }
        }
        
        # Enhanced figure settings
        self.figure_settings = {
            'dpi': IMAGE_DPI,
            'facecolor': 'white',
            'edgecolor': 'none',
            'bbox_inches': 'tight',
            'pad_inches': 0.1
        }
    
    def create_performance_comparison_plot(self, results_data: Dict[str, Any], 
                                         filename: str = "performance_comparison.png") -> bool:
        """Create an enhanced performance comparison plot."""
        if not MATPLOTLIB_AVAILABLE:
            logging.warning("matplotlib not available - skipping performance plot")
            return False
        
        try:
            # Prepare data for plotting
            algorithms = []
            execution_times = []
            memory_usages = []
            solution_costs = []
            violations = []
            
            for instance_name, instance_data in results_data.items():
                for algo in ['greedy', 'local', 'sa']:
                    if f'{algo}_time' in instance_data:
                        algorithms.append(f"{algo.title()} ({instance_name})")
                        execution_times.append(instance_data[f'{algo}_time'])
                        memory_usages.append(instance_data[f'{algo}_memory'])
                        solution_costs.append(instance_data[f'{algo}_cost'])
                        violations.append(instance_data[f'{algo}_violations'])
            
            if not algorithms:
                logging.warning("No data available for performance comparison plot")
                return False
            
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Algorithm Performance Comparison', fontsize=16, fontweight='bold')
            
            # Execution Time
            bars1 = ax1.bar(range(len(algorithms)), execution_times, 
                           color=[self.color_schemes['algorithms'].get(algo.split()[0], '#3498DB') 
                                 for algo in algorithms])
            ax1.set_title('Execution Time (seconds)', fontweight='bold')
            ax1.set_ylabel('Time (s)')
            ax1.set_xticks(range(len(algorithms)))
            ax1.set_xticklabels(algorithms, rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, value in zip(bars1, execution_times):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{value:.3f}', ha='center', va='bottom', fontsize=8)
            
            # Memory Usage
            bars2 = ax2.bar(range(len(algorithms)), memory_usages,
                           color=[self.color_schemes['algorithms'].get(algo.split()[0], '#E74C3C') 
                                 for algo in algorithms])
            ax2.set_title('Memory Usage (KB)', fontweight='bold')
            ax2.set_ylabel('Memory (KB)')
            ax2.set_xticks(range(len(algorithms)))
            ax2.set_xticklabels(algorithms, rotation=45, ha='right')
            
            # Solution Cost
            bars3 = ax3.bar(range(len(algorithms)), solution_costs,
                           color=[self.color_schemes['algorithms'].get(algo.split()[0], '#2ECC71') 
                                 for algo in algorithms])
            ax3.set_title('Solution Cost', fontweight='bold')
            ax3.set_ylabel('Cost')
            ax3.set_xticks(range(len(algorithms)))
            ax3.set_xticklabels(algorithms, rotation=45, ha='right')
            
            # Constraint Violations
            bars4 = ax4.bar(range(len(algorithms)), violations,
                           color=[self.color_schemes['performance']['critical'] if v > 0 
                                 else self.color_schemes['performance']['excellent'] 
                                 for v in violations])
            ax4.set_title('Constraint Violations', fontweight='bold')
            ax4.set_ylabel('Violations')
            ax4.set_xticks(range(len(algorithms)))
            ax4.set_xticklabels(algorithms, rotation=45, ha='right')
            
            plt.tight_layout()
            plt.savefig(filename, **self.figure_settings)
            plt.close()
            
            logging.info(f"Performance comparison plot saved: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating performance comparison plot: {e}")
            return False
    
    def create_algorithm_efficiency_radar(self, results_data: Dict[str, Any],
                                        filename: str = "algorithm_efficiency_radar.png") -> bool:
        """Create a radar chart showing algorithm efficiency across multiple metrics."""
        if not MATPLOTLIB_AVAILABLE:
            logging.warning("matplotlib not available - skipping radar chart")
            return False
        
        try:
            # Prepare normalized data for radar chart
            metrics = ['Speed', 'Memory Efficiency', 'Solution Quality', 'Constraint Satisfaction']
            algorithms = ['Greedy', 'Local Search', 'Simulated Annealing']
            
            # Calculate normalized scores for each algorithm
            algo_scores = {}
            
            for algo_key, algo_name in [('greedy', 'Greedy'), ('local', 'Local Search'), ('sa', 'Simulated Annealing')]:
                scores = []
                
                # Collect data across all instances
                times = []
                memories = []
                costs = []
                violations = []
                
                for instance_data in results_data.values():
                    if f'{algo_key}_time' in instance_data:
                        times.append(instance_data[f'{algo_key}_time'])
                        memories.append(instance_data[f'{algo_key}_memory'])
                        costs.append(instance_data[f'{algo_key}_cost'])
                        violations.append(instance_data[f'{algo_key}_violations'])
                
                if times:
                    # Normalize scores (higher is better)
                    avg_time = np.mean(times)
                    avg_memory = np.mean(memories)
                    avg_cost = np.mean(costs)
                    avg_violations = np.mean(violations)
                    
                    # Speed score (inverse of time, normalized)
                    speed_score = max(0, 1 - (avg_time / max(1, max(times) if times else 1)))
                    
                    # Memory efficiency (inverse of memory usage)
                    memory_score = max(0, 1 - (avg_memory / max(1, max(memories) if memories else 1)))
                    
                    # Solution quality (inverse of cost)
                    quality_score = max(0, 1 - (avg_cost / max(1, max(costs) if costs else 1)))
                    
                    # Constraint satisfaction (inverse of violations)
                    constraint_score = 1.0 if avg_violations == 0 else max(0, 1 - (avg_violations / 10))
                    
                    algo_scores[algo_name] = [speed_score, memory_score, quality_score, constraint_score]
            
            if not algo_scores:
                logging.warning("No data available for radar chart")
                return False
            
            # Create radar chart
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
            
            # Calculate angles for each metric
            angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
            angles += angles[:1]  # Complete the circle
            
            # Plot each algorithm
            colors = ['#E74C3C', '#3498DB', '#2ECC71']
            for i, (algo_name, scores) in enumerate(algo_scores.items()):
                scores += scores[:1]  # Complete the circle
                ax.plot(angles, scores, 'o-', linewidth=2, label=algo_name, color=colors[i])
                ax.fill(angles, scores, alpha=0.25, color=colors[i])
            
            # Customize the chart
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(metrics)
            ax.set_ylim(0, 1)
            ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
            ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'])
            ax.grid(True)
            
            plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
            plt.title('Algorithm Efficiency Comparison', size=16, fontweight='bold', pad=20)
            
            plt.tight_layout()
            plt.savefig(filename, **self.figure_settings)
            plt.close()
            
            logging.info(f"Algorithm efficiency radar chart saved: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating radar chart: {e}")
            return False
    
    def create_performance_heatmap(self, results_data: Dict[str, Any],
                                 filename: str = "performance_heatmap.png") -> bool:
        """Create a heatmap showing performance across instances and algorithms."""
        if not MATPLOTLIB_AVAILABLE or not PANDAS_AVAILABLE:
            logging.warning("matplotlib/pandas not available - skipping heatmap")
            return False
        
        try:
            # Prepare data matrix
            instances = list(results_data.keys())
            algorithms = ['Greedy', 'Local Search', 'Simulated Annealing']
            algo_keys = ['greedy', 'local', 'sa']
            
            # Create matrices for different metrics
            time_matrix = []
            memory_matrix = []
            cost_matrix = []
            
            for instance in instances:
                time_row = []
                memory_row = []
                cost_row = []
                
                for algo_key in algo_keys:
                    instance_data = results_data[instance]
                    time_row.append(instance_data.get(f'{algo_key}_time', 0))
                    memory_row.append(instance_data.get(f'{algo_key}_memory', 0))
                    cost_row.append(instance_data.get(f'{algo_key}_cost', 0))
                
                time_matrix.append(time_row)
                memory_matrix.append(memory_row)
                cost_matrix.append(cost_row)
            
            # Create subplots for different metrics
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
            
            # Time heatmap
            time_df = pd.DataFrame(time_matrix, index=instances, columns=algorithms)
            sns.heatmap(time_df, annot=True, fmt='.3f', cmap='YlOrRd', ax=ax1, cbar_kws={'label': 'Time (s)'})
            ax1.set_title('Execution Time', fontweight='bold')
            
            # Memory heatmap
            memory_df = pd.DataFrame(memory_matrix, index=instances, columns=algorithms)
            sns.heatmap(memory_df, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax2, cbar_kws={'label': 'Memory (KB)'})
            ax2.set_title('Memory Usage', fontweight='bold')
            
            # Cost heatmap
            cost_df = pd.DataFrame(cost_matrix, index=instances, columns=algorithms)
            sns.heatmap(cost_df, annot=True, fmt='.0f', cmap='RdYlGn_r', ax=ax3, cbar_kws={'label': 'Cost'})
            ax3.set_title('Solution Cost', fontweight='bold')
            
            plt.suptitle('Performance Heatmap Across Instances and Algorithms', fontsize=16, fontweight='bold')
            plt.tight_layout()
            plt.savefig(filename, **self.figure_settings)
            plt.close()
            
            logging.info(f"Performance heatmap saved: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating performance heatmap: {e}")
            return False
    
    def create_convergence_analysis(self, score_histories: Dict[str, List],
                                  filename: str = "convergence_analysis.png") -> bool:
        """Create detailed convergence analysis plots."""
        if not MATPLOTLIB_AVAILABLE:
            logging.warning("matplotlib not available - skipping convergence analysis")
            return False
        
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Algorithm Convergence Analysis', fontsize=16, fontweight='bold')
            
            colors = {'Simulated Annealing': '#E74C3C', 'Local Search': '#3498DB', 'Greedy': '#2ECC71'}
            
            for algo_name, history in score_histories.items():
                if not history:
                    continue
                
                # Extract data
                iterations = []
                scores = []
                
                for item in history:
                    if isinstance(item, tuple) and len(item) == 2:
                        iteration, data = item
                        if isinstance(data, dict):
                            iterations.append(iteration)
                            scores.append(data.get('score', data.get('cost', 0)))
                
                if not iterations:
                    continue
                
                color = colors.get(algo_name, '#333333')
                
                # Main convergence plot
                ax1.plot(iterations, scores, label=algo_name, color=color, linewidth=2)
                
                # Improvement rate (derivative)
                if len(scores) > 1:
                    improvements = np.diff(scores)
                    ax2.plot(iterations[1:], improvements, label=f"{algo_name} Improvement", 
                            color=color, alpha=0.7)
                
                # Cumulative improvement
                if scores:
                    initial_score = scores[0]
                    cumulative_improvement = [(initial_score - score) / initial_score * 100 
                                            for score in scores]
                    ax3.plot(iterations, cumulative_improvement, label=f"{algo_name} Cumulative", 
                            color=color, linewidth=2)
                
                # Moving average (smoothed convergence)
                if len(scores) > 5:
                    window_size = min(10, len(scores) // 3)
                    moving_avg = np.convolve(scores, np.ones(window_size)/window_size, mode='valid')
                    moving_iterations = iterations[window_size-1:]
                    ax4.plot(moving_iterations, moving_avg, label=f"{algo_name} Smoothed", 
                            color=color, linewidth=2, linestyle='--')
            
            # Customize subplots
            ax1.set_title('Score Evolution')
            ax1.set_xlabel('Iteration')
            ax1.set_ylabel('Score')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            ax2.set_title('Improvement Rate')
            ax2.set_xlabel('Iteration')
            ax2.set_ylabel('Score Change')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            ax3.set_title('Cumulative Improvement (%)')
            ax3.set_xlabel('Iteration')
            ax3.set_ylabel('Improvement (%)')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            ax4.set_title('Smoothed Convergence')
            ax4.set_xlabel('Iteration')
            ax4.set_ylabel('Score (Moving Average)')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(filename, **self.figure_settings)
            plt.close()
            
            logging.info(f"Convergence analysis saved: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating convergence analysis: {e}")
            return False


# Global enhanced visualization instance
_enhanced_viz = None

def get_enhanced_visualization():
    """Get the global enhanced visualization instance."""
    global _enhanced_viz
    if _enhanced_viz is None:
        _enhanced_viz = EnhancedVisualization()
    return _enhanced_viz

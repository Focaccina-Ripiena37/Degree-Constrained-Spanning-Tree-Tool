# app/config.py - Centralized configuration and constants for DCST Tool

"""
Centralized configuration module for the DCST (Degree-Constrained Spanning Tree) Tool.
This module contains all constants, default values, and configuration parameters
used throughout the application to ensure consistency and easy maintenance.
"""

#==============================================================================
#                           RESOURCE MANAGEMENT CONSTANTS
#==============================================================================

# Worker limits for parallel processing - ADAPTIVE SCALING
# These are now dynamic limits that scale with system capabilities
MAX_WORKERS_CONSERVATIVE = 3  # Conservative limit for modest systems
MAX_WORKERS_FALLBACK = 1  # Emergency fallback
MIN_CORES_FOR_OS = 2  # Always leave at least 2 cores for OS
MAX_IMAGE_WORKERS = 3  # Maximum workers for image generation (can be static)

# Resource safety margins and thresholds - ADAPTIVE
DEFAULT_SAFETY_MARGIN = 0.7  # Default safety margin for average systems
MIN_RAM_PER_WORKER = 0.8  # Minimum RAM per worker in GB
CPU_CHECK_INTERVAL = 1.0  # Check CPU every 1 second

# System classification thresholds for adaptive scaling
WORKSTATION_MIN_CORES = 12  # Minimum cores to be considered a workstation
WORKSTATION_MIN_RAM = 16.0  # Minimum RAM (GB) for workstation classification
DESKTOP_MIN_CORES = 8  # Minimum cores for desktop classification
DESKTOP_MIN_RAM = 8.0  # Minimum RAM (GB) for desktop classification

# Adaptive safety margins based on system type
WORKSTATION_SAFETY_MARGIN = 0.9  # Aggressive scaling for workstations
DESKTOP_SAFETY_MARGIN = 0.75  # Moderate scaling for desktops
LAPTOP_SAFETY_MARGIN = 0.5  # Conservative scaling for laptops/modest systems

# Adaptive worker calculation ratios
WORKSTATION_RAM_EFFICIENCY = 0.6  # Use 60% of available RAM for workers on workstations
DESKTOP_RAM_EFFICIENCY = 0.5  # Use 50% of available RAM for workers on desktops
LAPTOP_RAM_EFFICIENCY = 0.3  # Use 30% of available RAM for workers on laptops

# Memory thresholds (in GB)
MIN_MEMORY_GB = 1.0  # Minimum memory threshold
LOW_MEMORY_GB = 2.0  # Low memory threshold
LIMITED_MEMORY_GB = 4.0  # Limited memory threshold
RESERVED_RAM_RATIO = 0.4  # Reserve 40% of total RAM for OS

# CPU usage thresholds (in percentage)
CPU_THRESHOLD_HIGH = 90.0  # High CPU usage threshold
CPU_THRESHOLD_CRITICAL = 95.0  # Critical CPU usage threshold
CPU_THRESHOLD_AGGRESSIVE = 80.0  # Aggressive threshold for parallel operations
CPU_THRESHOLD_EDGE_SWAP = 75.0  # Threshold for edge swap operations
CPU_THRESHOLD_PARALLEL_LS = 70.0  # Threshold for parallel local search

#==============================================================================
#                           ALGORITHM PARAMETERS
#==============================================================================

# Default algorithm parameters
DEFAULT_PENALTY = 1000  # Default penalty for constraint violations
DEFAULT_MAX_CHILDREN = 3  # Default maximum children per node
DEFAULT_TIMEOUT = 300  # Default timeout in seconds (5 minutes)

# Simulated Annealing parameters
SA_INITIAL_TEMPERATURE = 200  # Default initial temperature
SA_COOLING_RATE = 0.98  # Default cooling rate
SA_MIN_TEMPERATURE = 0.01  # Default minimum temperature
SA_LARGE_INSTANCE_MIN_TEMP = 0.1  # Higher min temp for large instances
SA_LARGE_INSTANCE_COOLING = 0.9  # Faster cooling for large instances

# Local Search parameters
LS_MAX_ITERATIONS = 5000  # Default max iterations for local search
LS_LARGE_INSTANCE_MULTIPLIER = 2  # Multiplier for large instances
LS_LARGE_INSTANCE_MAX = 20000  # Maximum iterations for large instances
LS_NEIGHBORHOOD_SIZE = 1  # Default neighborhood size

# Graph size thresholds
LARGE_GRAPH_THRESHOLD = 1000  # Nodes threshold for large graph detection
PARALLEL_THRESHOLD_NODES = 100  # Minimum nodes for parallel processing
SEQUENTIAL_FORCE_THRESHOLD = 2000  # Force sequential for very large graphs

#==============================================================================
#                           TIMEOUT AND PERFORMANCE
#==============================================================================

# Timeout calculations
BASE_TIMEOUT = 300  # Base timeout in seconds
TIMEOUT_SIZE_FACTOR = 100  # Nodes per timeout unit
TIMEOUT_LOW_MEMORY_MAX = 180  # Max timeout for low memory (3 minutes)
TIMEOUT_LIMITED_MEMORY_MAX = 600  # Max timeout for limited memory (10 minutes)
TIMEOUT_HIGH_RESOURCE_MAX = 1800  # Max timeout for high resources (30 minutes)
TIMEOUT_MIN = 60  # Minimum timeout (1 minute)

# Parallel operation timeouts
PARALLEL_COST_EVAL_TIMEOUT_PER_CANDIDATE = 2  # Seconds per candidate
PARALLEL_COST_EVAL_TIMEOUT_MAX = 60  # Maximum timeout for cost evaluation
PARALLEL_EDGE_SWAP_TIMEOUT_PER_CANDIDATE = 1.5  # Seconds per candidate
PARALLEL_EDGE_SWAP_TIMEOUT_MAX = 40  # Maximum timeout for edge swap

# Individual task timeouts
INDIVIDUAL_TASK_TIMEOUT = 5  # Timeout for individual parallel tasks
EDGE_SWAP_TASK_TIMEOUT = 3  # Timeout for individual edge swap tasks

#==============================================================================
#                           ENVIRONMENT VARIABLES
#==============================================================================

# Environment variable names for CPU optimization
ENV_OMP_THREADS = "OMP_NUM_THREADS"
ENV_MKL_THREADS = "MKL_NUM_THREADS"
ENV_NUMEXPR_THREADS = "NUMEXPR_NUM_THREADS"
ENV_OPENBLAS_THREADS = "OPENBLAS_NUM_THREADS"

#==============================================================================
#                           FILE AND DIRECTORY CONSTANTS
#==============================================================================

# Directory naming
DEFAULT_PLOT_DIR_NAME = "Plot"
FALLBACK_PLOT_PREFIX = "Plot_fallback"
MAX_PLOT_DIRECTORIES = 9999

# Desktop directory fallback names for different locales
DESKTOP_FALLBACK_NAMES = ['Desktop', 'Escritorio', 'Bureau', 'Scrivania']

# File extensions and formats
IMAGE_FORMAT = "png"
IMAGE_DPI = 300
TABLE_IMAGE_DPI = 300

#==============================================================================
#                           GUI AND VISUALIZATION
#==============================================================================

# Progress reporting intervals
PROGRESS_REPORT_INTERVAL = 10  # Report progress every N iterations
PROGRESS_DETAILED_INTERVAL = 5  # Detailed progress every N iterations
PROGRESS_RESOURCE_CHECK_INTERVAL = 4  # Check resources every N progress reports

# Color schemes for visualization
NODE_COLORS = {
    "root": "#32CD32",  # Green for root node
    "violating": "#FF0000",  # Red for constraint-violating nodes
    "normal": "#3776ab",  # Blue for normal nodes
    "default": "#3776ab"  # Default blue
}

ALGORITHM_COLORS = {
    # Primary algorithm names (capitalized versions from GUI)
    "Greedy": "#D6EAF8",  # Light blue
    "Local": "#D5F5E3",  # Light green
    "Sa": "#FAE5D3",  # Light orange

    # Alternative names and variations
    "Simulated Annealing": "#FAE5D3",  # Same as Sa for compatibility
    "Local Search": "#D5F5E3",  # Same as Local
    "LocalSearch": "#D5F5E3",  # Same as Local
    "Greedy Algorithm": "#D6EAF8",  # Same as Greedy
    "SA": "#FAE5D3",  # Same as Sa
    "SimulatedAnnealing": "#FAE5D3",  # Same as Sa

    # Lowercase versions (for compatibility)
    "greedy": "#D6EAF8",  # Light blue
    "local": "#D5F5E3",  # Light green
    "sa": "#FAE5D3",  # Light orange

    # Italian versions (for compatibility with older code)
    "Algoritmo": "#D6EAF8",  # Default for unknown
    "Ricerca Locale": "#D5F5E3",  # Italian for Local Search
    "Ricottura Simulata": "#FAE5D3",  # Italian for Simulated Annealing

    # Enhanced colors for better visual distinction
    "Greedy_Enhanced": "#AED6F1",  # Slightly darker blue
    "Local_Enhanced": "#A9DFBF",  # Slightly darker green
    "Sa_Enhanced": "#F5B7B1",  # Slightly darker orange
}

EVOLUTION_PLOT_COLORS = {
    "Simulated Annealing": "#E74C3C",  # Bright red
    "Local Search": "#3498DB",  # Bright blue
    "Greedy": "#2ECC71"  # Bright green
}

# Figure sizes (width, height in inches)
GRAPH_FIGURE_SIZE = (8, 8)
TABLE_FIGURE_SIZE = (12, 6)
EVOLUTION_FIGURE_SIZE = (14, 8)

#==============================================================================
#                           LOGGING AND ERROR HANDLING
#==============================================================================

# Logging levels and formats
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Error handling
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.0  # Seconds between retries

#==============================================================================
#                           VALIDATION AND SAFETY
#==============================================================================

# Input validation limits
MAX_NODES_SMALL = 100
MAX_NODES_MEDIUM = 500
MAX_NODES_LARGE = 2000
MAX_PENALTY_VALUE = 100000
MIN_PENALTY_VALUE = 1

# Safety checks
EMERGENCY_CLEANUP_CPU_THRESHOLD = 98.0  # Trigger emergency cleanup
STABILITY_CHECK_INTERVAL = 0.5  # Seconds for stability checks

# User override settings (environment variables)
ENV_FORCE_CONSERVATIVE_MODE = "DCST_CONSERVATIVE_MODE"  # Force conservative limits
ENV_MAX_WORKERS_OVERRIDE = "DCST_MAX_WORKERS"  # User-specified max workers
ENV_SAFETY_MARGIN_OVERRIDE = "DCST_SAFETY_MARGIN"  # User-specified safety margin

# Adaptive scaling control
ENABLE_ADAPTIVE_SCALING = True  # Master switch for adaptive scaling
ADAPTIVE_SCALING_MIN_CORES = 4  # Minimum cores required for adaptive scaling
ADAPTIVE_SCALING_MIN_RAM = 4.0  # Minimum RAM (GB) required for adaptive scaling

#==============================================================================
#                           PERFORMANCE TUNING
#==============================================================================

# Cache and optimization settings
IMAGE_CACHE_ENABLED = True
PARALLEL_NEIGHBOR_THRESHOLD = 10  # Minimum neighbors for parallel generation
SMOOTHING_WINDOW_SIZE = 5  # Rolling average window for score evolution
SMOOTHING_MIN_POINTS = 3  # Minimum points required for smoothing

# Memory management
FORCE_GARBAGE_COLLECTION = True
GC_INTERVAL_ITERATIONS = 100  # Force GC every N iterations

#==============================================================================
#                           VERSION AND METADATA
#==============================================================================

# Application metadata
APP_VERSION = "1.0.0"
APP_NAME = "DCST Tool"
APP_DESCRIPTION = "Degree-Constrained Spanning Tree Optimization Tool"
APP_AUTHOR = "DCST Tool Team"

# Configuration version for compatibility checking
CONFIG_VERSION = "1.0.0"

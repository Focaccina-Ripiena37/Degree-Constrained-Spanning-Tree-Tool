"""
app/config.py — Minimal configuration for the simplified academic DCST Tool.

Only includes constants actually used by the lightweight GUI and utils.
"""

# Workers for async image generation in utils (thread pool size)
MAX_IMAGE_WORKERS = 3

# Desktop directory fallback names for different locales
DESKTOP_FALLBACK_NAMES = ['Desktop', 'Escritorio', 'Bureau', 'Scrivania']

# Plot directory naming
DEFAULT_PLOT_DIR_NAME = "Plot"
FALLBACK_PLOT_PREFIX = "Plot_fallback"
MAX_PLOT_DIRECTORIES = 9999

# Colors used by graph/table rendering
NODE_COLORS = {
    "root": "#32CD32",       # Green for root node
    "violating": "#FF0000",  # Red when degree exceeds constraint
    "normal": "#3776ab",     # Blue for normal nodes
    "default": "#3776ab",
}

ALGORITHM_COLORS = {
    # Standardized names used in GUI/outputs
    "Greedy": "#D6EAF8",
    "Local": "#D5F5E3",
    "SA": "#FAE5D3",
}

# Figure sizes and DPI
GRAPH_FIGURE_SIZE = (8, 8)
TABLE_FIGURE_SIZE = (12, 6)
IMAGE_DPI = 300
TABLE_IMAGE_DPI = 300

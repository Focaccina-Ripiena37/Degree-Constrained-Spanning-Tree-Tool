# app/gui.py - Application graphical interface

# Standard library imports
import os
import time
import queue
import logging
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
import json
import traceback
from datetime import datetime

# Lazy loading for heavy imports - will be loaded when needed
_heavy_imports_loaded = False
_pandas_loaded = False
_pil_loaded = False

def lazy_load_heavy_imports():
    """Lazy load heavy third-party libraries."""
    global _heavy_imports_loaded, pd, Image, ImageTk
    if not _heavy_imports_loaded:
        import pandas as pd
        from PIL import Image, ImageTk
        _heavy_imports_loaded = True
    return pd, Image, ImageTk

def lazy_load_algorithms():
    """Lazy load algorithm modules."""
    from .algorithms import test_instance, evaluate_solution
    from .utils import (
        generate_connected_random_graph,
        draw_and_save_graph,
        save_table_as_image,
        batch_generate_images,
        clear_image_cache,
        _cleanup_image_thread_pool,
        reset_plot_directory,
        get_current_plot_directory,
        detect_screen_size,
        calculate_optimal_window_size,
        get_screen_info
    )
    from .enhanced_visualization import get_enhanced_visualization
    from .performance_tracker import get_performance_tracker

    return (test_instance, evaluate_solution, generate_connected_random_graph,
            draw_and_save_graph, save_table_as_image, batch_generate_images,
            clear_image_cache, _cleanup_image_thread_pool, reset_plot_directory,
            get_current_plot_directory, detect_screen_size, calculate_optimal_window_size,
            get_screen_info, get_enhanced_visualization, get_performance_tracker)

def lazy_load_utils():
    """Lazy load utility functions for window sizing."""
    from .utils import detect_screen_size, calculate_optimal_window_size, get_screen_info
    return detect_screen_size, calculate_optimal_window_size, get_screen_info

# Essential imports only - others will be lazy loaded
from .platform_styles import platform_styles

# Class for handling log messages
class QueueHandler(logging.Handler):
    """Custom handler that sends log messages to the interface queue."""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        level_name = record.levelname.lower()
        level = "info"
        if level_name == "error" or level_name == "critical":
            level = "error"
        elif level_name == "warning":
            level = "warning"
        elif level_name == "info":
            level = "info"
        self.queue.put(("log", (msg, level)))

# Class for the application graphical interface
class App:
    def __init__(self, root, progress_bar):
        self.root = root
        self.progress_bar = progress_bar
        self.root.title("DCST Tool")

        # Configure platform-specific styling
        platform_styles.configure_window(self.root)
        self.colors = platform_styles.get_colors()

        # Initialize variables first (fast)
        self.init_variables()

        # Setup window sizing (fast)
        self.setup_adaptive_window_sizing()

        # Initialize UI components (fast)
        self.init_ui_components()

        # Schedule heavy initialization for after window is shown
        self.root.after(50, self.lazy_init_heavy_components)

    def init_variables(self):
        """Initialize control variables quickly."""
        # Control variables
        self.n_small = tk.IntVar(value=10)
        self.n_medium = tk.IntVar(value=50)
        self.n_large = tk.IntVar(value=200)

        # New p parameter system
        self.p_multiplier = tk.DoubleVar(value=1.0)  # Global multiplier (0x to 3x)
        self.p_small_base = tk.DoubleVar(value=0.4)  # Base p for small graphs
        self.p_medium_base = tk.DoubleVar(value=0.3)  # Base p for medium graphs
        self.p_large_base = tk.DoubleVar(value=0.15)  # Base p for large graphs
        self.advanced_mode = tk.BooleanVar(value=False)  # Advanced customization toggle

        # Legacy p_val for backward compatibility (will be calculated dynamically)
        self.p_val = tk.DoubleVar(value=0.3)

        self.max_children = tk.IntVar(value=3)
        self.penalty = tk.IntVar(value=1000)

    def init_ui_components(self):
        """Initialize basic UI components quickly."""
        # Variables for progress tracking
        self.current_algorithm = ""
        self.current_instance = ""
        self.current_phase = ""

        # Variable for computation thread
        self.computation_thread = None
        self.stop_event = threading.Event()
        self.queue_running = True  # Flag to control the queue thread

        # Labels and input fields
        self.create_widgets()

        # Note: Heavy initialization is already scheduled in __init__, no need to schedule again

        # Progress bar (placed in scrollable area)
        progress_container = platform_styles.create_frame(self.scrollable_frame)
        progress_container.pack(fill="x", pady=5)

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=5)

        # Label for progress bar status
        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=2)

        # Text area with scrollbar for execution details - Increased size
        self.log_frame = platform_styles.create_frame(self.scrollable_frame)
        self.log_frame.pack(fill="both", expand=True, padx=12, pady=8)

        # Label for the log
        self.log_header = platform_styles.create_label(self.log_frame, "Performance Details", style_type='primary')
        self.log_header.configure(anchor="w", font=platform_styles.get_font(11, 'bold'))
        self.log_header.pack(fill="x", padx=8, pady=4)

        # Use platform-appropriate colors for log text - Increased height
        log_bg = self.colors.get('bg_secondary', '#1e1e1e')
        log_fg = self.colors.get('text_secondary', '#cccccc')
        # FIX: use scrolledtext.ScrolledText (not tk.scrolledtext)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=12, bg=log_bg, fg=log_fg,
                                                wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text.config(state=tk.DISABLED)  # Read-only

        # Configure text tags for different log levels and performance metrics
        self.log_text.tag_config("timestamp", foreground="#999999")
        self.log_text.tag_config("info", foreground="#cccccc")
        self.log_text.tag_config("success", foreground="#00cc00")
        self.log_text.tag_config("warning", foreground="#ffcc00")
        self.log_text.tag_config("error", foreground="#ff3333")
        self.log_text.tag_config("highlight", foreground="#3399ff")
        self.log_text.tag_config("performance", foreground="#ff9900")  # Orange for performance metrics

        # Panel for dynamic parameters - Improved layout with increased size
        self.dynamic_params_frame = tk.LabelFrame(self.scrollable_frame, text="Real-time Parameters",
                                                bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                                font=platform_styles.get_font(10, 'bold'),
                                                relief="groove", bd=3)
        self.dynamic_params_frame.pack(fill="x", padx=12, pady=(8, 15), ipady=8)

        # Configure columns for uniform distribution
        for i in range(3):
            self.dynamic_params_frame.columnconfigure(i, weight=1, uniform="equal")

        # First row: Main algorithm parameters - Increased font size and padding
        self.iter_label = tk.Label(self.dynamic_params_frame, text="Iterations: -",
                                 bg=self.colors['bg_primary'], fg=self.colors['text_accent'],
                                 font=platform_styles.get_font(9, 'bold'),
                                 anchor="w", width=16)
        self.iter_label.grid(row=0, column=0, padx=10, pady=6, sticky="ew")

        self.temp_label = tk.Label(self.dynamic_params_frame, text="Temperature: -",
                                 bg=self.colors['bg_primary'], fg=self.colors['text_accent'],
                                 font=platform_styles.get_font(9, 'bold'),
                                 anchor="w", width=16)
        self.temp_label.grid(row=0, column=1, padx=10, pady=6, sticky="ew")

        self.cost_label = tk.Label(self.dynamic_params_frame, text="Current Cost: -",
                                 bg=self.colors['bg_primary'], fg=self.colors['success_color'],
                                 font=platform_styles.get_font(9, 'bold'),
                                 anchor="w", width=16)
        self.cost_label.grid(row=0, column=2, padx=10, pady=6, sticky="ew")

        # Second row: Performance metrics - Increased font size and padding
        self.accepted_label = tk.Label(self.dynamic_params_frame, text="Acceptances: -",
                                     bg=self.colors['bg_primary'], fg=self.colors['success_color'],
                                     font=platform_styles.get_font(9, 'bold'),
                                     anchor="w", width=16)
        self.accepted_label.grid(row=1, column=0, padx=10, pady=6, sticky="ew")

        self.plateau_label = tk.Label(self.dynamic_params_frame, text="Plateau: -",
                                    bg=self.colors['bg_primary'], fg=self.colors['warning_color'],
                                    font=platform_styles.get_font(9, 'bold'),
                                    anchor="w", width=16)
        self.plateau_label.grid(row=1, column=1, padx=10, pady=6, sticky="ew")

        self.reheat_label = tk.Label(self.dynamic_params_frame, text="Reheat: -",
                                   bg=self.colors['bg_primary'], fg=self.colors['warning_color'],
                                   font=platform_styles.get_font(9, 'bold'),
                                   anchor="w", width=16)
        self.reheat_label.grid(row=1, column=2, padx=10, pady=6, sticky="ew")

        # Third row: Space for future additional metrics (optional)
        # This row can be used to add new metrics without modifying the layout
        self.extra_metric1_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg=self.colors['bg_primary'], fg=self.colors['text_secondary'],
                                          font=platform_styles.get_font(8),
                                          anchor="w", width=15)
        self.extra_metric1_label.grid(row=2, column=0, padx=8, pady=2, sticky="ew")

        self.extra_metric2_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg=self.colors['bg_primary'], fg=self.colors['text_secondary'],
                                          font=platform_styles.get_font(8),
                                          anchor="w", width=15)
        self.extra_metric2_label.grid(row=2, column=1, padx=8, pady=2, sticky="ew")

        self.extra_metric3_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg=self.colors['bg_primary'], fg=self.colors['text_secondary'],
                                          font=platform_styles.get_font(8),
                                          anchor="w", width=15)
        self.extra_metric3_label.grid(row=2, column=2, padx=8, pady=2, sticky="ew")

        # Queue for communication between threads
        self.queue = queue.Queue()
        self.queue_handler = QueueHandler(self.queue)
        logging.getLogger().addHandler(self.queue_handler)

        # Start the thread for queue processing
        self.queue_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.queue_thread.start()

        # Close the terminal when the window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_adaptive_window_sizing(self):
        """
        Setup adaptive window sizing based on screen resolution and enable scrolling.
        Compatible with Windows, macOS, and Linux.
        """
        try:
            # Lazy load utility functions
            detect_screen_size, calculate_optimal_window_size, get_screen_info = lazy_load_utils()

            # Get screen information
            screen_info = get_screen_info()

            # Log screen detection results
            print(f"🖥️ Screen detected: {screen_info['screen_width']}x{screen_info['screen_height']} "
                  f"({screen_info['scale_factor']}) - DPI: {screen_info['dpi']:.0f}")

            # Calculate optimal window size
            optimal_width = screen_info['optimal_width']
            optimal_height = screen_info['optimal_height']

            # Ensure minimum size for multi-column layout
            min_width = 1000   # Increased for multi-column layout
            min_height = 800   # Adequate height for expanded sections

            final_width = max(min_width, optimal_width)
            final_height = max(min_height, optimal_height)

            # Use more screen space for multi-column layout
            final_width = min(final_width, int(screen_info['screen_width'] * 0.75))  # Use up to 75% of screen width
            final_height = min(final_height, int(screen_info['screen_height'] * 0.85))  # Use up to 85% of screen height
            
            # Center the window on screen
            screen_width = screen_info['screen_width']
            screen_height = screen_info['screen_height']
            x = (screen_width - final_width) // 4
            y = (screen_height - final_height) // 4

            # Set window geometry
            geometry = f"{final_width}x{final_height}+{x}+{y}"
            self.root.geometry(geometry)

            # Store window info for later use
            self.window_info = {
                'width': final_width,
                'height': final_height,
                'screen_info': screen_info
            }

            # Make window resizable
            self.root.resizable(True, True)

            # Set minimum window size
            self.root.minsize(min_width, min_height)

            print(f"📐 Window sized: {final_width}x{final_height} (centered at {x},{y})")

        except Exception as e:
            print(f"⚠️ Adaptive sizing failed: {e}")
            # Fallback to multi-column layout size but centered
            try:
                # Try to use lazy loaded functions if available
                try:
                    detect_screen_size, calculate_optimal_window_size, get_screen_info = lazy_load_utils()
                    screen_width, screen_height = detect_screen_size()
                except:
                    # Ultimate fallback if utils can't be loaded
                    screen_width, screen_height = 1200, 800

                fallback_width, fallback_height = 1000, 800  # Multi-column layout size
                x = (screen_width - fallback_width) // 2
                y = (screen_height - fallback_height) // 2
                self.root.geometry(f"{fallback_width}x{fallback_height}+{x}+{y}")
                self.root.resizable(True, True)
                self.root.minsize(1000, 800)  # Multi-column minimum size
                print(f"📐 Fallback window: {fallback_width}x{fallback_height}")
            except:
                # Ultimate fallback - multi-column layout
                self.root.geometry("1000x800")  # Multi-column layout size
                self.root.resizable(True, True)
                self.root.minsize(1000, 800)
                print("📐 Using default window size")

    def setup_mouse_wheel_scrolling(self, scrollable_frame):
        """
        Setup mouse wheel scrolling for the main content area.
        Works across Windows, macOS, and Linux.
        """
        def on_mousewheel(event):
            # Different platforms handle mouse wheel differently
            if event.delta:
                # Windows and macOS
                delta = -1 * (event.delta / 120)
            else:
                # Linux
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                else:
                    return

            # Scroll the canvas
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.yview_scroll(int(delta), "units")

        # Bind mouse wheel events for different platforms
        def bind_mousewheel(widget):
            # Windows and macOS
            widget.bind("<MouseWheel>", on_mousewheel)
            # Linux
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)

        # Bind to the main window and scrollable frame
        bind_mousewheel(self.root)
        if scrollable_frame:
            bind_mousewheel(scrollable_frame)

        # Also bind to child widgets recursively
        def bind_to_children(widget):
            bind_mousewheel(widget)
            for child in widget.winfo_children():
                bind_to_children(child)

        # Bind to all existing children
        bind_to_children(self.root)

    def create_scrollable_container(self):
        """
        Create a scrollable container for the main interface.
        This allows the interface to be scrolled when content doesn't fit.
        """
        # Create main container frame using platform styling
        self.main_container = platform_styles.create_frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Create canvas and scrollbar using platform colors
        canvas_bg = self.colors.get('canvas_bg', self.colors['bg_primary'])
        self.canvas = tk.Canvas(self.main_container, bg=canvas_bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)

        # Create scrollable frame using platform styling
        self.scrollable_frame = platform_styles.create_frame(self.canvas)

        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind canvas resize to update scrollable frame width
        def on_canvas_configure(event):
            # Update the scrollable frame width to match canvas width
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)

        self.canvas.bind("<Configure>", on_canvas_configure)

        # Setup mouse wheel scrolling
        self.setup_mouse_wheel_scrolling(self.scrollable_frame)

        # Bind mouse wheel to canvas as well
        def on_canvas_mousewheel(event):
            # Different platforms handle mouse wheel differently
            if event.delta:
                # Windows and macOS
                delta = -1 * (event.delta / 120)
            else:
                # Linux
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                else:
                    return

            self.canvas.yview_scroll(int(delta), "units")

        # Bind mouse wheel events to canvas
        self.canvas.bind("<MouseWheel>", on_canvas_mousewheel)  # Windows and macOS
        self.canvas.bind("<Button-4>", on_canvas_mousewheel)    # Linux
        self.canvas.bind("<Button-5>", on_canvas_mousewheel)    # Linux

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with multi-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 2-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=400)  # Left column (parameters)
        main_frame.grid_columnconfigure(1, weight=3, minsize=500)  # Right column (controls & details)
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning both columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))

        # Create left column (Parameter Input)
        self.create_left_column(main_frame)

        # Create right column (Controls and Details)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Parameter input section
        param_label = platform_styles.create_label(left_frame, "Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes using platform styling with improved spacing
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=8, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=8, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=8, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=8, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=8, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=8, sticky='ew')

        # Input for max_children (k) using platform styling with improved spacing
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=8, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=8, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=8, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=8, sticky='ew')

        # Connection multiplier section
        multiplier_label = platform_styles.create_label(left_frame, "Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(20, 10), sticky='w')

        # Global multiplier slider
        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=10, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=10, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=5)

        # Advanced mode checkbox with better spacing
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=15, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_right_column(self, parent):
        """Create the right column with controls and details."""
        # Right column frame
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=10)

        # Configure right frame grid
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Make details section expandable

        # Control buttons section
        control_label = platform_styles.create_label(right_frame, "Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 15), sticky='w')

        # Button frame for better organization
        button_frame = platform_styles.create_frame(right_frame)
        button_frame.grid(row=1, column=0, pady=(0, 20), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        # Button to start calculations - larger and more prominent
        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=20)
        start_button.grid(row=0, column=0, pady=10, padx=(0, 10), sticky='ew')

        # Button to stop calculations - larger and more prominent
        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=20)
        stop_button.grid(row=0, column=1, pady=10, padx=(10, 0), sticky='ew')

        # Progress section
        progress_label = platform_styles.create_label(right_frame, "Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=2, column=0, pady=(20, 10), sticky='w')

        # Progress bar container
        progress_container = platform_styles.create_frame(right_frame)
        progress_container.grid(row=3, column=0, sticky='ew', pady=(0, 10))

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=5, fill='x')

        # Label for progress bar status
        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=2)

        # Real-time Parameters section (expanded)
        self.create_realtime_params_section(right_frame)

        # Performance Details section (expanded)
        self.create_performance_details_section(right_frame)

        # Status details
        self.status_details = platform_styles.create_label(right_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)  # Increased wrap length for right column
        self.status_details.grid(row=7, column=0, pady=8, sticky='ew')

    def create_realtime_params_section(self, parent):
        """Create the real-time parameters section (expanded)."""
        # Panel for dynamic parameters - Expanded layout
        self.dynamic_params_frame = tk.LabelFrame(parent, text="Real-time Parameters",
                                                bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                                font=platform_styles.get_font(12, 'bold'),
                                                relief="groove", bd=3)
        self.dynamic_params_frame.grid(row=4, column=0, sticky='ew', padx=0, pady=(10, 15), ipady=12)

        # Configure columns for uniform distribution
        for i in range(3):
            self.dynamic_params_frame.columnconfigure(i, weight=1, uniform="equal")

        # First row: Main algorithm parameters - Increased font size and padding
        self.iter_label = tk.Label(self.dynamic_params_frame, text="Iterations: -",
                                 bg=self.colors['bg_primary'], fg=self.colors['text_accent'],
                                 font=platform_styles.get_font(10, 'bold'),
                                 anchor="w", width=18)
        self.iter_label.grid(row=0, column=0, padx=12, pady=8, sticky="ew")

        self.temp_label = tk.Label(self.dynamic_params_frame, text="Temperature: -",
                                 bg=self.colors['bg_primary'], fg=self.colors['text_accent'],
                                 font=platform_styles.get_font(10, 'bold'),
                                 anchor="w", width=18)
        self.temp_label.grid(row=0, column=1, padx=12, pady=8, sticky="ew")

        self.cost_label = tk.Label(self.dynamic_params_frame, text="Current Cost: -",
                                 bg=self.colors['bg_primary'], fg=self.colors['success_color'],
                                 font=platform_styles.get_font(10, 'bold'),
                                 anchor="w", width=18)
        self.cost_label.grid(row=0, column=2, padx=12, pady=8, sticky="ew")

        # Second row: Performance metrics - Increased font size and padding
        self.accepted_label = tk.Label(self.dynamic_params_frame, text="Acceptances: -",
                                     bg=self.colors['bg_primary'], fg=self.colors['success_color'],
                                     font=platform_styles.get_font(10, 'bold'),
                                     anchor="w", width=18)
        self.accepted_label.grid(row=1, column=0, padx=12, pady=8, sticky="ew")

        self.plateau_label = tk.Label(self.dynamic_params_frame, text="Plateau: -",
                                    bg=self.colors['bg_primary'], fg=self.colors['warning_color'],
                                    font=platform_styles.get_font(10, 'bold'),
                                    anchor="w", width=18)
        self.plateau_label.grid(row=1, column=1, padx=12, pady=8, sticky="ew")

        self.reheat_label = tk.Label(self.dynamic_params_frame, text="Reheat: -",
                                   bg=self.colors['bg_primary'], fg=self.colors['warning_color'],
                                   font=platform_styles.get_font(10, 'bold'),
                                   anchor="w", width=18)
        self.reheat_label.grid(row=1, column=2, padx=12, pady=8, sticky="ew")

    def create_performance_details_section(self, parent):
        """Create the performance details section (expanded)."""
        # Text area with scrollbar for execution details - Expanded size
        self.log_frame = platform_styles.create_frame(parent)
        self.log_frame.grid(row=5, column=0, sticky='nsew', pady=(15, 10))

        # Label for the log
        self.log_header = platform_styles.create_label(self.log_frame, "Performance Details", style_type='primary')
        self.log_header.configure(anchor="w", font=platform_styles.get_font(12, 'bold'))
        self.log_header.pack(fill="x", padx=8, pady=4)

        # Use platform-appropriate colors for log text - Expanded height
        log_bg = self.colors.get('bg_secondary', '#1e1e1e')
        log_fg = self.colors.get('text_secondary', '#cccccc')
        # FIX: use scrolledtext.ScrolledText (not tk.scrolledtext)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=15, bg=log_bg, fg=log_fg,
                                                wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text.config(state=tk.DISABLED)  # Read-only

        # Configure text tags for different log levels and performance metrics
        self.log_text.tag_config("timestamp", foreground="#999999")
        self.log_text.tag_config("info", foreground="#cccccc")
        self.log_text.tag_config("success", foreground="#00cc00")
        self.log_text.tag_config("warning", foreground="#ffcc00")
        self.log_text.tag_config("error", foreground="#ff3333")
        self.log_text.tag_config("highlight", foreground="#3399ff")
        self.log_text.tag_config("performance", foreground="#ff9900")  # Orange for performance metrics

    def lazy_init_heavy_components(self):
        """Initialize heavy components after the main window is shown."""
        try:
            # Load heavy imports when needed
            lazy_load_heavy_imports()

            # Initialize any heavy components here
            # (Currently most heavy initialization is done on-demand)

        except Exception as e:
            logging.error(f"Error in lazy initialization: {e}")

    def create_footer(self):
        """Create footer section with GitHub logo and University text."""
        # Footer frame - add to main scrollable frame
        footer_frame = platform_styles.create_frame(self.scrollable_frame)
        footer_frame.pack(fill="x", padx=15, pady=(20, 15), side="bottom")

        # Configure footer grid
        footer_frame.grid_columnconfigure(0, weight=1)  # Left spacer
        footer_frame.grid_columnconfigure(1, weight=0)  # GitHub icon
        footer_frame.grid_columnconfigure(2, weight=0)  # University text
        footer_frame.grid_columnconfigure(3, weight=1)  # Right spacer

        # Add GitHub icon
        self.add_github_icon_to_footer(footer_frame)

        # Add University text
        university_label = platform_styles.create_label(footer_frame, "University of Ferrara - 2025", style_type='secondary')
        university_label.configure(font=platform_styles.get_font(9), anchor="w")
        university_label.grid(row=0, column=2, padx=(10, 0), pady=5, sticky="w")

    def add_github_icon_to_footer(self, footer_frame):
        """Add GitHub icon to footer."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "github.png")
            if os.path.exists(icon_path):
                # Lazy load PIL when needed
                pd, Image, ImageTk = lazy_load_heavy_imports()
                pil_image = Image.open(icon_path)
                # Resize icon to be smaller for footer
                pil_image = pil_image.resize((20, 20), Image.Resampling.LANCZOS)
                github_icon = ImageTk.PhotoImage(pil_image)
                github_button = tk.Button(
                    footer_frame,
                    image=github_icon,
                    command=self.open_github,
                    bg=self.colors['bg_primary'],
                    borderwidth=0,
                    highlightthickness=0,
                    relief='flat',
                    cursor='hand2'
                )
                # Store reference to prevent garbage collection
                github_button.image = github_icon
                github_button.grid(row=0, column=1, padx=(0, 5), pady=5)
                return  # Success, no need for fallback
            else:
                pass  # GitHub icon file not found, will use fallback
        except Exception:
            pass  # Error loading GitHub icon, will use fallback

        # Fallback to text link if icon fails or doesn't exist
        github_text = tk.Label(
            footer_frame,
            text="GitHub",
            fg=self.colors['text_accent'],
            bg=self.colors['bg_primary'],
            font=platform_styles.get_font(9, 'underline'),
            cursor='hand2'
        )
        github_text.bind("<Button-1>", lambda e: self.open_github())
        github_text.grid(row=0, column=1, padx=(0, 5), pady=5)

    def open_github(self):
        webbrowser.open("https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git")

    def create_advanced_p_controls(self, frame):
        """Create the advanced p parameter controls (initially hidden)."""
        # Configure column weights for better alignment
        frame.columnconfigure(2, weight=1, minsize=20)  # Spacer column

        # Create column header for connection probability
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.max_children, width=12).grid(row=4, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Penalty:").grid(row=5, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.penalty, width=12).grid(row=5, column=1, padx=10, pady=6, sticky='ew')

        # Connection settings
        multiplier_label = platform_styles.create_label(left_frame, "🔗 Connection Settings", style_type='primary')
        multiplier_label.configure(font=platform_styles.get_font(12, 'bold'))
        multiplier_label.grid(row=6, column=0, columnspan=2, pady=(16, 8), sticky='w')

        platform_styles.create_label(left_frame, "Connection Multiplier:").grid(row=7, column=0, padx=10, pady=8, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(left_frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=7, column=1, padx=10, pady=8, sticky='ew')

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(left_frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10, 'bold'))
        self.multiplier_label.grid(row=8, column=0, columnspan=2, padx=10, pady=4)

        # Advanced mode
        self.advanced_checkbox = platform_styles.create_checkbutton(left_frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Advanced controls (initially hidden)
        self.create_advanced_p_controls(left_frame)

    def create_center_column(self, parent):
        """Create the center column with controls and progress/status."""
        center_frame = platform_styles.create_frame(parent)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        center_frame.grid_columnconfigure(0, weight=1)

        # Optimization Controls
        control_label = platform_styles.create_label(center_frame, "⚙️ Optimization Controls", style_type='primary')
        control_label.configure(font=platform_styles.get_font(14, 'bold'))
        control_label.grid(row=0, column=0, pady=(0, 12), sticky='w')

        button_frame = platform_styles.create_frame(center_frame)
        button_frame.grid(row=1, column=0, pady=(0, 16), sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        start_button = platform_styles.create_button(button_frame, "Start Optimization",
                                                    command=self.start_computation,
                                                    style_type='primary', width=16)
        start_button.grid(row=0, column=0, pady=6, padx=(0, 8), sticky='ew')

        stop_button = platform_styles.create_button(button_frame, "Stop Optimization",
                                                   command=self.stop_computation,
                                                   style_type='error', width=16)
        stop_button.grid(row=0, column=1, pady=6, padx=(8, 0), sticky='ew')

        # Separator
        ttk.Separator(center_frame, orient='horizontal').grid(row=2, column=0, sticky='ew', pady=(4, 10))

        # Progress & Status (single instance in the app)
        progress_label = platform_styles.create_label(center_frame, "📊 Progress & Status", style_type='primary')
        progress_label.configure(font=platform_styles.get_font(12, 'bold'))
        progress_label.grid(row=3, column=0, pady=(0, 8), sticky='w')

        progress_container = platform_styles.create_frame(center_frame)
        progress_container.grid(row=4, column=0, sticky='ew')

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=6, fill='x')

        self.progress_label = platform_styles.create_label(progress_container, "Ready to start...")
        self.progress_label.pack(pady=(0, 4))

        # Detailed status below
        self.status_details = platform_styles.create_label(center_frame, "", style_type='accent')
        self.status_details.configure(wraplength=600)
        self.status_details.grid(row=5, column=0, pady=(10, 0), sticky='ew')

    def create_right_column(self, parent):
        """Create the right column with real-time parameters and performance details."""
        right_frame = platform_styles.create_frame(parent)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)  # Performance details expandable

        # Real-time Parameters section
        realtime_label = platform_styles.create_label(right_frame, "📈 Real-time Parameters", style_type='primary')
        realtime_label.configure(font=platform_styles.get_font(14, 'bold'))
        realtime_label.grid(row=0, column=0, pady=(0, 10), sticky='w')

        self.create_realtime_params_section(right_frame)

        # Separator between sections
        ttk.Separator(right_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=(8, 12))

        # Performance Details section
        perf_label = platform_styles.create_label(right_frame, "📜 Performance Details", style_type='primary')
        perf_label.configure(font=platform_styles.get_font(12, 'bold'))
        perf_label.grid(row=2, column=0, pady=(0, 8), sticky='w')

        self.create_performance_details_section(right_frame)

    def create_widgets(self):
        # Create main container with scrollable area
        self.create_scrollable_container()

        # Create the main content frame with 3-column layout
        main_frame = platform_styles.create_frame(self.scrollable_frame)
        main_frame.pack(pady=15, fill="both", expand=True)

        # Configure main frame for 3-column layout
        main_frame.grid_columnconfigure(0, weight=2, minsize=360)  # Left: Parameters
        main_frame.grid_columnconfigure(1, weight=2, minsize=360)  # Center: Controls + Progress
        main_frame.grid_columnconfigure(2, weight=3, minsize=420)  # Right: Real-time + Performance
        main_frame.grid_rowconfigure(0, weight=0)  # Title row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row

        # Title spanning all columns
        title_label = platform_styles.create_label(main_frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # Create left, center, and right columns
        self.create_left_column(main_frame)
        self.create_center_column(main_frame)
        self.create_right_column(main_frame)

        # Footer section with GitHub logo and University text
        self.create_footer()

    def create_left_column(self, parent):
        """Create the left column with parameter inputs."""
        # Left column frame
        left_frame = platform_styles.create_frame(parent)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)

        # Configure left frame grid
        left_frame.grid_columnconfigure(1, weight=1)

        # Section title
        param_label = platform_styles.create_label(left_frame, "🧩 Instance Parameters", style_type='primary')
        param_label.configure(font=platform_styles.get_font(14, 'bold'))
        param_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Input for number of nodes (compact and clear)
        platform_styles.create_label(left_frame, "Small Instance:").grid(row=1, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_small, width=12).grid(row=1, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Medium Instance:").grid(row=2, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_medium, width=12).grid(row=2, column=1, padx=10, pady=6, sticky='ew')

        platform_styles.create_label(left_frame, "Large Instance:").grid(row=3, column=0, padx=10, pady=6, sticky='w')
        platform_styles.create_entry(left_frame, textvariable=self.n_large, width=12).grid(row=3, column=1, padx=10, pady=6, sticky='ew')

        # Max children and penalty
        platform_styles.create_label(left_frame, "Maximum Children:").grid(row=4, column=0, padx=10, pady=6, sticky='w')
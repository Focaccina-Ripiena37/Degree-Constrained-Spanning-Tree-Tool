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
from datetime import datetime

# Third-party library imports
import pandas as pd
from PIL import Image, ImageTk

# Local algorithm imports
from .algorithms import test_instance
from .platform_styles import platform_styles
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

        # Implement adaptive window sizing based on screen resolution
        self.setup_adaptive_window_sizing()

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

        # Progress bar (placed in scrollable area)
        progress_container = tk.Frame(self.scrollable_frame, bg="#2b2b2b")
        progress_container.pack(fill="x", pady=5)

        self.progress_bar = ttk.Progressbar(progress_container, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=5)

        # Label for progress bar status
        self.progress_label = tk.Label(progress_container, text="Ready to start...", fg="white", bg="#2b2b2b")
        self.progress_label.pack(pady=2)

        # Text area with scrollbar for execution details
        self.log_frame = tk.Frame(self.scrollable_frame, bg="#2b2b2b")
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Label for the log
        self.log_header = tk.Label(self.log_frame, text="Performance Details", bg="#2b2b2b", fg="white", anchor="w", font=("Arial", 10, "bold"))
        self.log_header.pack(fill="x", padx=5, pady=2)

        self.log_text = tk.scrolledtext.ScrolledText(self.log_frame, height=10, bg="#1e1e1e", fg="#cccccc",
                                                wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state=tk.DISABLED)  # Read-only

        # Configure text tags for different log levels and performance metrics
        self.log_text.tag_config("timestamp", foreground="#999999")
        self.log_text.tag_config("info", foreground="#cccccc")
        self.log_text.tag_config("success", foreground="#00cc00")
        self.log_text.tag_config("warning", foreground="#ffcc00")
        self.log_text.tag_config("error", foreground="#ff3333")
        self.log_text.tag_config("highlight", foreground="#3399ff")
        self.log_text.tag_config("performance", foreground="#ff9900")  # Orange for performance metrics

        # Panel for dynamic parameters - Improved layout
        self.dynamic_params_frame = tk.LabelFrame(self.scrollable_frame, text="Real-time Parameters",
                                                bg="#2b2b2b", fg="white",
                                                font=("Arial", 9, "bold"),
                                                relief="groove", bd=2)
        self.dynamic_params_frame.pack(fill="x", padx=10, pady=(5, 10))

        # Configure columns for uniform distribution
        for i in range(3):
            self.dynamic_params_frame.columnconfigure(i, weight=1, uniform="equal")

        # First row: Main algorithm parameters
        self.iter_label = tk.Label(self.dynamic_params_frame, text="Iterations: -",
                                 bg="#2b2b2b", fg="#87CEEB", font=("Arial", 8, "bold"),
                                 anchor="w", width=15)
        self.iter_label.grid(row=0, column=0, padx=8, pady=4, sticky="ew")

        self.temp_label = tk.Label(self.dynamic_params_frame, text="Temperature: -",
                                 bg="#2b2b2b", fg="#87CEEB", font=("Arial", 8, "bold"),
                                 anchor="w", width=15)
        self.temp_label.grid(row=0, column=1, padx=8, pady=4, sticky="ew")

        self.cost_label = tk.Label(self.dynamic_params_frame, text="Current Cost: -",
                                 bg="#2b2b2b", fg="#90EE90", font=("Arial", 8, "bold"),
                                 anchor="w", width=15)
        self.cost_label.grid(row=0, column=2, padx=8, pady=4, sticky="ew")

        # Second row: Performance metrics
        self.accepted_label = tk.Label(self.dynamic_params_frame, text="Acceptances: -",
                                     bg="#2b2b2b", fg="#90EE90", font=("Arial", 8, "bold"),
                                     anchor="w", width=15)
        self.accepted_label.grid(row=1, column=0, padx=8, pady=4, sticky="ew")

        self.plateau_label = tk.Label(self.dynamic_params_frame, text="Plateau: -",
                                    bg="#2b2b2b", fg="#FFA500", font=("Arial", 8, "bold"),
                                    anchor="w", width=15)
        self.plateau_label.grid(row=1, column=1, padx=8, pady=4, sticky="ew")

        self.reheat_label = tk.Label(self.dynamic_params_frame, text="Reheat: -",
                                   bg="#2b2b2b", fg="#FFA500", font=("Arial", 8, "bold"),
                                   anchor="w", width=15)
        self.reheat_label.grid(row=1, column=2, padx=8, pady=4, sticky="ew")

        # Third row: Space for future additional metrics (optional)
        # This row can be used to add new metrics without modifying the layout
        self.extra_metric1_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg="#2b2b2b", fg="#DDA0DD", font=("Arial", 8),
                                          anchor="w", width=15)
        self.extra_metric1_label.grid(row=2, column=0, padx=8, pady=2, sticky="ew")

        self.extra_metric2_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg="#2b2b2b", fg="#DDA0DD", font=("Arial", 8),
                                          anchor="w", width=15)
        self.extra_metric2_label.grid(row=2, column=1, padx=8, pady=2, sticky="ew")

        self.extra_metric3_label = tk.Label(self.dynamic_params_frame, text="",
                                          bg="#2b2b2b", fg="#DDA0DD", font=("Arial", 8),
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
            # Get screen information
            screen_info = get_screen_info()

            # Log screen detection results
            print(f"🖥️ Screen detected: {screen_info['screen_width']}x{screen_info['screen_height']} "
                  f"({screen_info['scale_factor']}) - DPI: {screen_info['dpi']:.0f}")

            # Calculate optimal window size
            optimal_width = screen_info['optimal_width']
            optimal_height = screen_info['optimal_height']

            # Ensure minimum size for usability - increased default sizes
            min_width = 600   # Increased from 450 for better usability
            min_height = 800  # Increased from 700 for better layout

            final_width = max(min_width, optimal_width)
            final_height = max(min_height, optimal_height)

            # Use more of the available screen space
            final_width = min(final_width, int(screen_info['screen_width'] * 0.6))  # Use up to 60% of screen width
            final_height = min(final_height, int(screen_info['screen_height'] * 0.8))  # Use up to 80% of screen height
            
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
            # Fallback to larger default size but centered
            try:
                screen_width, screen_height = detect_screen_size()
                fallback_width, fallback_height = 600, 800  # Increased from 225, 920
                x = (screen_width - fallback_width) // 2
                y = (screen_height - fallback_height) // 2
                self.root.geometry(f"{fallback_width}x{fallback_height}+{x}+{y}")
                self.root.resizable(True, True)
                self.root.minsize(600, 800)  # Increased minimum size
                print(f"📐 Fallback window: {fallback_width}x{fallback_height}")
            except:
                # Ultimate fallback - larger default
                self.root.geometry("600x800")  # Increased from 450x920
                self.root.resizable(True, True)
                self.root.minsize(600, 800)
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
        self.canvas = tk.Canvas(self.main_container, bg=self.colors['bg_primary'], highlightthickness=0)
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

        # Create the main content frame inside the scrollable area using platform styling
        frame = platform_styles.create_frame(self.scrollable_frame)
        frame.pack(pady=10, fill="both", expand=True)

        # Title (centered above inputs) using platform styling
        title_label = platform_styles.create_label(frame, "DCST Tool", style_type='title')
        title_label.configure(font=platform_styles.get_font(18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))

        # Add GitHub icon
        self.add_github_icon(frame)

        # Input for number of nodes using platform styling
        platform_styles.create_label(frame, "Small Instance:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        platform_styles.create_entry(frame, textvariable=self.n_small, width=10).grid(row=1, column=1, padx=5, pady=5)

        platform_styles.create_label(frame, "Medium Instance:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        platform_styles.create_entry(frame, textvariable=self.n_medium, width=10).grid(row=2, column=1, padx=5, pady=5)

        platform_styles.create_label(frame, "Large Instance:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        platform_styles.create_entry(frame, textvariable=self.n_large, width=10).grid(row=3, column=1, padx=5, pady=5)

        # Input for max_children (k) using platform styling
        platform_styles.create_label(frame, "Maximum Children:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        platform_styles.create_entry(frame, textvariable=self.max_children, width=10).grid(row=4, column=1, padx=5, pady=5)

        platform_styles.create_label(frame, "Penalty:").grid(row=5, column=0, padx=5, pady=5, sticky='w')
        platform_styles.create_entry(frame, textvariable=self.penalty, width=10).grid(row=5, column=1, padx=5, pady=5)

        # New p parameter system using platform styling
        # Global multiplier slider
        platform_styles.create_label(frame, "Connection Multiplier:").grid(row=6, column=0, padx=5, pady=5, sticky='w')
        self.p_multiplier_scale = platform_styles.create_scale(frame, variable=self.p_multiplier, from_=0, to=3,
                                                              resolution=0.1, orient="horizontal",
                                                              command=self.on_multiplier_change)
        self.p_multiplier_scale.grid(row=6, column=1, padx=5, pady=5)

        # Multiplier value label
        self.multiplier_label = platform_styles.create_label(frame, "1.0x", style_type='accent')
        self.multiplier_label.configure(font=platform_styles.get_font(10))
        self.multiplier_label.grid(row=6, column=2, padx=5, pady=5)

        # Advanced mode checkbox
        self.advanced_checkbox = platform_styles.create_checkbutton(frame, "Advanced Mode",
                                                                   variable=self.advanced_mode,
                                                                   command=self.toggle_advanced_mode)
        self.advanced_checkbox.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Advanced p sliders (initially hidden)
        self.create_advanced_p_controls(frame)

        # Button to start calculations using platform styling
        start_button = platform_styles.create_button(frame, "Start", command=self.start_computation,
                                                    style_type='primary')
        start_button.grid(row=12, column=0, pady=20, padx=10)

        # Button to stop calculations using platform styling
        stop_button = platform_styles.create_button(frame, "Stop", command=self.stop_computation,
                                                   style_type='error')
        stop_button.grid(row=12, column=1, pady=20, padx=10)

        # Configuration management buttons using platform styling
        config_frame = platform_styles.create_frame(frame)
        config_frame.grid(row=13, column=0, columnspan=4, pady=10)

        export_config_btn = platform_styles.create_button(config_frame, "Export Config",
                                                         command=self.export_configuration,
                                                         style_type='secondary', width=15)
        export_config_btn.grid(row=0, column=0, padx=10)

        import_config_btn = platform_styles.create_button(config_frame, "Import Config",
                                                         command=self.import_configuration,
                                                         style_type='success', width=15)
        import_config_btn.grid(row=0, column=1, padx=10)

        # Label for status details using platform styling
        self.status_details = platform_styles.create_label(self.scrollable_frame, "", style_type='accent')
        self.status_details.configure(wraplength=400)  # Increased wrap length for larger window
        self.status_details.pack(pady=5)

    def add_github_icon(self, frame):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "github.png")
            if os.path.exists(icon_path):
                pil_image = Image.open(icon_path)
                github_icon = ImageTk.PhotoImage(pil_image)
                github_button = tk.Button(
                    frame,
                    image=github_icon,
                    command=self.open_github,
                    bg="#2b2b2b",
                    borderwidth=0
                )
                github_button.image = github_icon
                github_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")  # Positioned to the right of the title
            else:
                print(f"File not found: {icon_path}")
        except Exception as e:
            print(f"Error loading icon: {str(e)}")

    def open_github(self):
        webbrowser.open("https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git")

    def create_advanced_p_controls(self, frame):
        """Create the advanced p parameter controls (initially hidden)."""
        # Configure column weights for better alignment
        frame.columnconfigure(2, weight=1, minsize=20)  # Spacer column

        # Create column header for connection probability
        self.connection_prob_header = tk.Label(frame, text="Connection probability",
                                             fg="white", bg="#2b2b2b",
                                             font=("Arial", 10, "bold"))
        self.connection_prob_header.grid(row=8, column=0, columnspan=2, padx=(20, 5), pady=(5, 2), sticky="w")

        # Small graph p slider
        self.p_small_label = tk.Label(frame, text="Small:", fg="white", bg="#2b2b2b")
        self.p_small_label.grid(row=9, column=0, padx=(30, 5), pady=2, sticky="w")
        self.p_small_scale = tk.Scale(frame, variable=self.p_small_base, from_=0, to=1, resolution=0.01,
                                     orient="horizontal", bg="#2b2b2b", fg="white", length=100)
        self.p_small_scale.grid(row=9, column=1, padx=(5, 10), pady=2, sticky="w")

        # Medium graph p slider
        self.p_medium_label = tk.Label(frame, text="Medium:", fg="white", bg="#2b2b2b")
        self.p_medium_label.grid(row=10, column=0, padx=(30, 5), pady=2, sticky="w")
        self.p_medium_scale = tk.Scale(frame, variable=self.p_medium_base, from_=0, to=1, resolution=0.01,
                                      orient="horizontal", bg="#2b2b2b", fg="white", length=100)
        self.p_medium_scale.grid(row=10, column=1, padx=(5, 10), pady=2, sticky="w")

        # Large graph p slider
        self.p_large_label = tk.Label(frame, text="Large:", fg="white", bg="#2b2b2b")
        self.p_large_label.grid(row=11, column=0, padx=(30, 5), pady=2, sticky="w")
        self.p_large_scale = tk.Scale(frame, variable=self.p_large_base, from_=0, to=1, resolution=0.01,
                                     orient="horizontal", bg="#2b2b2b", fg="white", length=100)
        self.p_large_scale.grid(row=11, column=1, padx=(5, 10), pady=2, sticky="w")

        # Initially hide all advanced controls
        self.hide_advanced_controls()

    def hide_advanced_controls(self):
        """Hide the advanced p parameter controls."""
        self.connection_prob_header.grid_remove()
        self.p_small_label.grid_remove()
        self.p_small_scale.grid_remove()
        self.p_medium_label.grid_remove()
        self.p_medium_scale.grid_remove()
        self.p_large_label.grid_remove()
        self.p_large_scale.grid_remove()

    def show_advanced_controls(self):
        """Show the advanced p parameter controls."""
        self.connection_prob_header.grid()
        self.p_small_label.grid()
        self.p_small_scale.grid()
        self.p_medium_label.grid()
        self.p_medium_scale.grid()
        self.p_large_label.grid()
        self.p_large_scale.grid()

    def toggle_advanced_mode(self):
        """Toggle between normal and advanced parameter mode."""
        if self.advanced_mode.get():
            # Enable advanced mode
            self.show_advanced_controls()
            self.p_multiplier_scale.config(state='disabled')
            self.multiplier_label.config(text="Disabled", fg="#888888")
        else:
            # Disable advanced mode
            self.hide_advanced_controls()
            self.p_multiplier_scale.config(state='normal')
            self.on_multiplier_change(self.p_multiplier.get())

    def on_multiplier_change(self, value):
        """Update the multiplier label when the multiplier slider changes."""
        if not self.advanced_mode.get():
            multiplier = float(value)
            self.multiplier_label.config(text=f"{multiplier:.1f}x", fg="#87CEEB")

    def get_p_value_for_size(self, size_name):
        """Get the appropriate p value for a given graph size."""
        if self.advanced_mode.get():
            # Use individual p values in advanced mode
            if size_name == "small":
                return float(self.p_small_base.get())
            elif size_name == "medium":
                return float(self.p_medium_base.get())
            elif size_name == "large":
                return float(self.p_large_base.get())
        else:
            # Use base values multiplied by global multiplier
            multiplier = float(self.p_multiplier.get())
            if size_name == "small":
                return min(1.0, float(self.p_small_base.get()) * multiplier)
            elif size_name == "medium":
                return min(1.0, float(self.p_medium_base.get()) * multiplier)
            elif size_name == "large":
                return min(1.0, float(self.p_large_base.get()) * multiplier)

        # Fallback to default
        return 0.3

    def check_p_parameters(self):
        """Check p parameters for critical values and show warnings."""
        if self.advanced_mode.get():
            # Check individual p values in advanced mode
            p_small = float(self.p_small_base.get())
            p_medium = float(self.p_medium_base.get())
            p_large = float(self.p_large_base.get())

            # Check each p value
            for p_val, size_name, field_name in [(p_small, "small", "p_small_base"),
                                                 (p_medium, "medium", "p_medium_base"),
                                                 (p_large, "large", "p_large_base")]:
                if p_val < 0.1:
                    warning_msg = (
                        f"⚠️ Low connectivity detected for {size_name} instance!\n\n"
                        f"The connection degree is {p_val:.2f} (< 0.1).\n"
                        "This could cause:\n"
                        "• Disconnected or poorly connected graph\n"
                        "• Algorithm failures\n"
                        "• Significant slowdowns\n"
                        "• Poor quality solutions\n\n"
                        "PERFORMANCE IMPACT:\n"
                        "• Algorithms might not find valid solutions\n"
                        "• Unpredictable execution times\n"
                        "• Possible errors during optimization\n"
                        "• Non-representative results"
                    )
                    safe_value = 0.4 if size_name == "small" else (0.3 if size_name == "medium" else 0.15)
                    if not self.show_critical_confirmation(warning_msg, field_name, p_val, safe_value):
                        return False
        else:
            # Check multiplier mode - calculate effective p values
            multiplier = float(self.p_multiplier.get())
            p_small_eff = min(1.0, float(self.p_small_base.get()) * multiplier)
            p_medium_eff = min(1.0, float(self.p_medium_base.get()) * multiplier)
            p_large_eff = min(1.0, float(self.p_large_base.get()) * multiplier)

            # Check if any effective p value is too low
            for p_val, size_name in [(p_small_eff, "small"), (p_medium_eff, "medium"), (p_large_eff, "large")]:
                if p_val < 0.1:
                    warning_msg = (
                        f"⚠️ Low connectivity detected for {size_name} instance!\n\n"
                        f"The effective connection degree is {p_val:.2f} (< 0.1).\n"
                        f"Current multiplier: {multiplier:.1f}x\n\n"
                        "This could cause:\n"
                        "• Disconnected or poorly connected graph\n"
                        "• Algorithm failures\n"
                        "• Significant slowdowns\n"
                        "• Poor quality solutions\n\n"
                        "RECOMMENDATION:\n"
                        "Increase the multiplier or switch to advanced mode\n"
                        "for individual parameter control."
                    )
                    if not self.show_critical_confirmation(warning_msg, "p_multiplier", multiplier, 1.0):
                        return False
                    break  # Only show one warning for multiplier mode

        return True

    def show_critical_warning(self, message):
        """Show a critical warning to the user."""
        messagebox.showwarning("Critical Warning", message)

    def show_critical_confirmation(self, message, field_name, current_value, safe_value):
        """
        Show a critical warning with confirmation options to the user.

        Args:
            message: Warning message to show
            field_name: Name of the field with critical value
            current_value: Current (critical) value
            safe_value: Safe value to restore if user cancels

        Returns:
            bool: True if user chooses to proceed, False if cancels
        """
        # Add confirmation options to the message
        confirmation_message = message + "\n\n" + (
            "🤔 WHAT DO YOU WANT TO DO?\n\n"
            "• PROCEED: Continue with current values (at your own risk)\n"
            "• CANCEL: Restore safe values and modify parameters\n\n"
            "⚠️ IMPORTANT: If you proceed, you accept responsibility\n"
            "for any performance or system stability issues."
        )

        # Show confirmation dialog
        result = messagebox.askyesno(
            "⚠️ Confirm Critical Parameters",
            confirmation_message,
            icon='warning'
        )

        if result:
            # User chose "Yes" (Proceed)
            self.log_message(f"⚠️ WARNING: User confirmed use of critical parameters: {field_name}={current_value}", "warning")
            return True
        else:
            # User chose "No" (Cancel) - restore safe value
            self.revert_field_to_safe_value(field_name, safe_value)
            self.log_message(f"✅ Parameter {field_name} restored to safe value: {safe_value}", "info")
            return False

    def revert_field_to_safe_value(self, field_name, safe_value):
        """
        Restore a field to its safe value.

        Args:
            field_name: Name of the field to restore
            safe_value: Safe value to set
        """
        try:
            if field_name == "n_large":
                self.n_large.set(safe_value)
            elif field_name == "n_medium":
                self.n_medium.set(safe_value)
            elif field_name == "n_small":
                self.n_small.set(safe_value)
            elif field_name == "p_val":
                self.p_val.set(safe_value)
            elif field_name == "p_multiplier":
                self.p_multiplier.set(safe_value)
            elif field_name == "p_small_base":
                self.p_small_base.set(safe_value)
            elif field_name == "p_medium_base":
                self.p_medium_base.set(safe_value)
            elif field_name == "p_large_base":
                self.p_large_base.set(safe_value)
            elif field_name == "penalty":
                self.penalty.set(safe_value)

            # Show restoration confirmation message
            messagebox.showinfo(
                "Value Restored",
                f"The parameter '{field_name}' has been restored to safe value: {safe_value}\n\n"
                "You can now modify the parameters with safer values before starting the calculation."
            )

        except Exception as e:
            self.log_message(f"Error restoring field {field_name}: {e}", "error")

    def validate_inputs(self):
        """Verify that the entered values are consistent and display an error message if they are not."""
        try:
            n_small = int(self.n_small.get())
            n_medium = int(self.n_medium.get())
            n_large = int(self.n_large.get())
        except ValueError:
            messagebox.showerror("Input Error", "Values must be integers.")
            return False

        if n_small <= 0 or n_medium <= 0 or n_large <= 0:
            messagebox.showerror("Input Error", "Values must be positive numbers greater than zero.")
            return False

        if not (n_small < n_medium < n_large):
            messagebox.showerror("Input Error", "Values must respect the hierarchy:\n"
                                                    "Small Instance < Medium Instance < Large Instance")
            return False

        # Checks for critical parameter warnings with user confirmation
        if not self.check_critical_parameters():
            return False  # User canceled due to critical parameters

        return True

    def check_critical_parameters(self):
        """
        Check critical parameters and show warnings with user confirmation.

        Returns:
            bool: True if all parameters are acceptable or confirmed by user, False otherwise
        """
        # 1. CRITICAL check for large graph
        n_large = int(self.n_large.get())
        if n_large >= 1000:
            warning_msg = (
                "🔴 HIGH RISK OF SYSTEM CRASH!\n\n"
                f"The large instance has {n_large} nodes (≥ 1000).\n"
                "THIS CAN CAUSE:\n"
                "• CRITICAL SYSTEM CRASH (0xc000012d)\n"
                "• COMPLETE PC FREEZE\n"
                "• LOSS OF UNSAVED DATA\n"
                "• FORCED SYSTEM RESTART\n\n"
                "🛑 STRONG RECOMMENDATION:\n"
                "Reduce to less than 800 nodes to avoid crashes.\n"
                "The system is configured in SAFE MODE but graphs\n"
                "of this size remain dangerous."
            )
            if not self.show_critical_confirmation(warning_msg, "n_large", n_large, 500):
                return False  # User canceled
        elif n_large >= 800:
            warning_msg = (
                "⚠️ WARNING: Critical size graph!\n\n"
                f"The large instance has {n_large} nodes (≥ 800).\n"
                "This could cause:\n"
                "• Very long execution times (>30 min)\n"
                "• High memory consumption (>8GB)\n"
                "• Possible system slowdowns\n"
                "• Automatic algorithm timeouts\n\n"
                "🛡️ The system is in SAFE MODE but it's recommended\n"
                "to carefully monitor performance."
            )
            if not self.show_critical_confirmation(warning_msg, "n_large", n_large, 500):
                return False  # User canceled
        elif n_large >= 500:
            warning_msg = (
                "⚠️ Large graph detected!\n\n"
                f"The large instance has {n_large} nodes (≥ 500).\n"
                "This could cause:\n"
                "• Long execution times (10-20 min)\n"
                "• High memory consumption (4-8GB)\n"
                "• Parallelization automatically disabled\n\n"
                "ℹ️ The system will use sequential algorithms for safety.\n"
                "PERFORMANCE IMPACT:\n"
                "• Intensive CPU usage for 10-20 minutes\n"
                "• Memory consumption up to 4-8GB\n"
                "• Possible slowdowns of other applications"
            )
            if not self.show_critical_confirmation(warning_msg, "n_large", n_large, 200):
                return False  # User canceled

        # 2. Check for low connectivity (new p system)
        if not self.check_p_parameters():
            return False  # User canceled

        # 3. Check for low penalty
        penalty = int(self.penalty.get())
        if penalty < 100:
            warning_msg = (
                "⚠️ Low penalty value detected!\n\n"
                f"The penalty is {penalty} (< 100).\n"
                "This could cause:\n"
                "• Tree cost distortion\n"
                "• Difficulty in solution comparison\n"
                "• Insignificant results\n"
                "• Degree constraint violations not adequately penalized\n\n"
                "IMPACT ON RESULT QUALITY:\n"
                "• Degree constraints might be ignored\n"
                "• Non-significant algorithm comparisons\n"
                "• Solutions not conforming to problem requirements\n"
                "• Distorted evaluation metrics"
            )
            if not self.show_critical_confirmation(warning_msg, "penalty", penalty, 1000):
                return False  # User canceled

        # All checks passed or confirmed by user
        return True

    def start_computation(self):
        """Start calculations for all instances."""
        self.reset_progress_bar()
        self.progress_label.config(text="Ready to start...")

        if not self.validate_inputs():
            return

        self.stop_event.clear()

        # Start a separate thread to execute calculations
        self.computation_thread = threading.Thread(target=self.run_optimization, daemon=True)
        self.computation_thread.start()

    def stop_computation(self):
        """Stop ongoing calculations."""
        if self.computation_thread and self.computation_thread.is_alive():
            # Set the stop event
            self.stop_event.set()
            self.queue.put(("status", "Stopping in progress..."))
            self.queue.put(("progress", 0))  # Reset the progress bar

            # Wait for the computation thread to terminate (with timeout)
            self.computation_thread.join(timeout=5)  # Wait at most 5 seconds
            if self.computation_thread.is_alive():
                logging.warning("Computation thread did not terminate within timeout.")

            # Save partial results
            self.save_partial_results()

            # Notify the user
            self.queue.put(("status", "Calculation stopped by user. Saving partial results..."))
            messagebox.showinfo("Stopped", "Execution has been stopped. Partial results have been saved.")

    def save_partial_results(self):
        """Save partial results generated up to that point."""
        try:
            results = getattr(self, "results", {})  # Retrieve partial results
            if not results:
                logging.info("No partial results to save.")
                return

            plot_dir = get_current_plot_directory()

            for size_name, instance_results in results.items():
                if "graph" in instance_results:
                    graph_filename = os.path.join(plot_dir, f"partial_graph_{size_name}.png")
                    draw_and_save_graph(instance_results["graph"], graph_filename, max_children=self.max_children.get(), is_spanning_tree=False)

                for algo in ["greedy", "local", "sa"]:
                    tree_key = f"{algo}_tree"
                    if tree_key in instance_results:
                        tree_filename = os.path.join(plot_dir, f"partial_{algo}_tree_{size_name}.png")
                        draw_and_save_graph(instance_results[tree_key], tree_filename, max_children=self.max_children.get(), is_spanning_tree=True)

            # Salva anche le tabelle parziali
            table_data = []
            for size_name, metrics in results.items():
                for algo in ["greedy", "local", "sa"]:
                    algo_key = f"{algo}_cost"
                    if algo_key in metrics:
                        row = {
                            "Istanza": size_name,
                            "Algoritmo": algo.capitalize(),
                            "Costo": metrics[algo_key],
                            "Tempo (s)": round(metrics[f"{algo}_time"], 4),
                            "Chiamate": metrics[f"{algo}_calls"],
                            "Memoria (KB)": round(metrics[f"{algo}_memory"], 2),
                            "Violazioni": metrics.get(f"{algo}_violations", 0)
                        }
                        table_data.append(row)

            if table_data:
                # Calcola i punteggi per i risultati parziali
                from .algorithms import evaluate_solution

                # Calcola i valori massimi per la normalizzazione
                max_cost = max(row["Costo"] for row in table_data)
                max_time = max(row["Tempo (s)"] for row in table_data)
                max_memory = max(row["Memoria (KB)"] for row in table_data)
                max_violations = max(row["Violazioni"] for row in table_data)

                reference_values = {
                    "max_cost": max_cost,
                    "max_time": max_time,
                    "max_memory": max_memory,
                    "max_violations": max_violations
                }

                # Calcola il punteggio per ogni riga
                for row in table_data:
                    solution_data = {
                        "cost": row["Costo"],
                        "execution_time": row["Tempo (s)"],
                        "memory": row["Memoria (KB)"],
                        "violations": row["Violazioni"]
                    }

                    score = evaluate_solution(solution_data, reference_values)
                    row["Punteggio"] = score

                df = pd.DataFrame(table_data)
                table_filename = os.path.join(plot_dir, "partial_results_table.png")
                save_table_as_image(df, table_filename)
                logging.info(f"Partial table saved: {table_filename}")

            # Also generate partial temporal graphs if available
            from .utils import plot_score_evolution

            for size_name, instance_results in results.items():
                score_histories = {}

                if "local_score_history" in instance_results and instance_results["local_score_history"]:
                    score_histories["Local Search"] = instance_results["local_score_history"]

                if "sa_score_history" in instance_results and instance_results["sa_score_history"]:
                    score_histories["Simulated Annealing"] = instance_results["sa_score_history"]

                if score_histories:
                    # Calculate partial reference values
                    all_costs = []
                    all_times = []
                    all_memories = []
                    all_violations = []

                    for algo in ["greedy", "local", "sa"]:
                        if f"{algo}_cost" in instance_results:
                            all_costs.append(instance_results[f"{algo}_cost"])
                        if f"{algo}_time" in instance_results:
                            all_times.append(instance_results[f"{algo}_time"])
                        if f"{algo}_memory" in instance_results:
                            all_memories.append(instance_results[f"{algo}_memory"])
                        if f"{algo}_violations" in instance_results:
                            all_violations.append(instance_results[f"{algo}_violations"])

                    reference_final_values = {
                        "max_cost": max(all_costs) if all_costs else 1,
                        "max_time": max(all_times) if all_times else 1,
                        "max_memory": max(all_memories) if all_memories else 1,
                        "max_violations": max(all_violations) if all_violations else 1
                    }

                    evolution_filename = f"partial_score_evolution_{size_name}.png"
                    success = plot_score_evolution(score_histories, reference_final_values, evolution_filename)
                    if success:
                        logging.info(f"Partial evolution graph saved for {size_name}")

            logging.info("Partial results saved successfully.")

        except Exception as e:
            logging.error(f"Error saving partial results: {e}")

    def log_message(self, message, level="info"):
        """Add a message to the log with timestamp."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Color style mapping based on level
        # Color mapping is handled by text tags, no need for explicit color variable

        # Highlight performance metrics in normal messages
        if level in ["info", "success"] and any(x in message.lower() for x in ["cost=", "time=", "calls=", "memory=", "iterations="]):
            # Message with performance metrics
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")

            # Separate and format message parts with metrics
            parts = []
            current_part = ""
            for segment in message.split(", "):
                if any(x in segment.lower() for x in ["cost=", "time=", "calls=", "memory=", "iterations=", "acceptances="]):
                    if current_part:
                        parts.append((current_part, level))
                        current_part = ""
                    parts.append((segment, "performance"))
                else:
                    current_part += (", " if current_part else "") + segment

            if current_part:
                parts.append((current_part, level))

            for part, tag in parts:
                self.log_text.insert(tk.END, part + (", " if tag == "performance" and part != parts[-1][0] else ""), tag)

            self.log_text.insert(tk.END, "\n")
        else:
            # Normal message
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.log_text.insert(tk.END, f"{message}\n", level)

        self.log_text.see(tk.END)  # Automatically scroll to the end
        self.log_text.config(state=tk.DISABLED)  # Return to read-only mode

    def reset_progress_bar(self):
        """Reset the progress bar and status labels with improved layout."""
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Ready to start...")

        # Reset dynamic parameter labels with logical order
        self.iter_label.config(text="Iterations: -")
        self.temp_label.config(text="Temperature: -")
        self.cost_label.config(text="Current Cost: -")
        self.accepted_label.config(text="Acceptances: -")
        self.plateau_label.config(text="Plateau: -")
        self.reheat_label.config(text="Reheat: -")
        # Reset extra labels
        self.extra_metric1_label.config(text="")
        self.extra_metric2_label.config(text="")
        self.extra_metric3_label.config(text="")

    def on_closing(self):
        """Handle the main window closing."""
        if messagebox.askokcancel("Exit", "Do you really want to exit?"):
            self.queue_running = False  # Stop the queue thread
            self.stop_event.set()  # Stop any ongoing calculations
            self.root.destroy()

    def process_queue(self):
        """Process messages in the queue for GUI updates."""
        while self.queue_running:
            try:
                msg_type, msg_value = self.queue.get(block=True, timeout=0.1)

                self.root.after(0, self._process_message, msg_type, msg_value)

            except queue.Empty:
                time.sleep(0.01)  # Brief pause to avoid saturating the CPU
            except Exception as e:
                print(f"Error during queue processing: {e}")

    def _process_message(self, msg_type, msg_value):
        """Process a single message from the queue (called from main thread)."""
        try:
            if msg_type == "temperature":
                self.temp_label.config(text=f"Temperature: {msg_value}")
            elif msg_type == "iteration":
                self.iter_label.config(text=f"Iterations: {msg_value}")
            elif msg_type == "cost":
                self.cost_label.config(text=f"Current Cost: {msg_value}")
            elif msg_type == "plateau":
                self.plateau_label.config(text=f"Plateau: {msg_value}")
            elif msg_type == "reheats":
                self.reheat_label.config(text=f"Reheat: {msg_value}")
            elif msg_type == "accepted":
                self.accepted_label.config(text=f"Acceptances: {msg_value}")
            elif msg_type == "log":
                msg, level = msg_value
                self.log_message(msg, level)
            elif msg_type == "progress":
                self.progress_bar['value'] = msg_value
                self.progress_label.config(text=f"Progress: {msg_value}%")
            elif msg_type == "status":
                self.progress_label.config(text=msg_value)
            elif msg_type == "phase":
                self.status_details.config(text=msg_value)
            elif msg_type == "instance":
                self.current_instance = msg_value
            elif msg_type == "algorithm":
                self.current_algorithm = msg_value
            elif msg_type == "error":
                messagebox.showerror("Error", msg_value)
                self.reset_progress_bar()
            elif msg_type == "reset_labels":
                # Reset dynamic parameter labels with improved layout
                self.iter_label.config(text="Iterations: -")
                self.temp_label.config(text="Temperature: -")
                self.cost_label.config(text="Current Cost: -")
                self.accepted_label.config(text="Acceptances: -")
                self.plateau_label.config(text="Plateau: -")
                self.reheat_label.config(text="Reheat: -")
                # Reset extra labels (if used)
                self.extra_metric1_label.config(text="")
                self.extra_metric2_label.config(text="")
                self.extra_metric3_label.config(text="")
        except Exception as e:
            print(f"Error processing message {msg_type}: {e}")

    def run_optimization(self):
        """
        Execute calculation for all instances (small, medium, large)
        with detailed status updates.
        """
        try:
            # Reset plot directory for new calculation session
            reset_plot_directory()

            # Get the new plot directory and inform the user
            plot_dir = get_current_plot_directory()
            self.queue.put(("log", (f"📁 Results will be saved in: {plot_dir}", "info")))
        except Exception as e:
            import traceback
            traceback.print_exc()
            return

        # Store results for later saving
        self.results = {}

        # Get instance sizes from main thread before starting background work
        # This fixes the "main thread is not in main loop" error
        try:
            instances = {
                "small": self.n_small.get(),
                "medium": self.n_medium.get(),
                "large": self.n_large.get()
            }
            max_children = self.max_children.get()
            penalty = self.penalty.get()
        except Exception as e:
            self.queue.put(("error", f"Error reading GUI parameters: {e}"))
            return

        # Reset dynamic parameter labels using queue system (thread-safe)
        self.queue.put(("reset_labels", None))

        try:
            # Total progress = 100 units per instance
            # Calculate weighted steps based on instance size
            total_nodes = sum(instances.values())
            weighted_instances = {name: (size/total_nodes) * 100 for name, size in instances.items()}

            self.queue.put(("log", ("Initializing optimization...", "info")))

            # Log parameter information based on mode
            if self.advanced_mode.get():
                self.queue.put(("log", (f"Parameters: max_children={self.max_children.get()}, penalty={self.penalty.get()}", "info")))
                self.queue.put(("log", (f"Advanced Mode: p_small={self.p_small_base.get():.3f}, p_medium={self.p_medium_base.get():.3f}, p_large={self.p_large_base.get():.3f}", "info")))
            else:
                multiplier = self.p_multiplier.get()
                self.queue.put(("log", (f"Parameters: max_children={self.max_children.get()}, penalty={self.penalty.get()}, multiplier={multiplier:.1f}x", "info")))
                self.queue.put(("log", (f"Effective P: small={self.get_p_value_for_size('small'):.3f}, medium={self.get_p_value_for_size('medium'):.3f}, large={self.get_p_value_for_size('large'):.3f}", "info")))

            # Reset overall progress
            overall_progress = 0
            self.queue.put(("progress", overall_progress))

            for instance_name, n_nodes in instances.items():
                if self.stop_event.is_set():
                    self.queue.put(("log", ("Calculation stopped by user.", "warning")))
                    break

                # Calculate instance weight for progress bar
                instance_weight = weighted_instances[instance_name]
                instance_progress_start = overall_progress

                # Get the appropriate p value for this graph size
                p_value = self.get_p_value_for_size(instance_name)

                # Update for new instance
                self.queue.put(("instance", instance_name))
                self.queue.put(("log", (f"Generating connected random graph with {n_nodes} nodes and p={p_value:.3f}...", "info")))

                # Update progress bar for graph generation phase (10% of instance)
                graph_gen_progress = instance_progress_start + (instance_weight * 0.1)
                self.queue.put(("progress", int(graph_gen_progress)))
                self.queue.put(("phase", f"Graph generation for {instance_name} instance"))

                # Generate the graph
                try:
                    G = generate_connected_random_graph(n_nodes, p_value)
                    self.queue.put(("log", (f"Graph generated: {n_nodes} nodes, {len(G.edges())} edges", "success")))
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.queue.put(("error", f"Error in graph generation: {e}"))
                    return

                # Update progress after graph generation (15% of instance progress)
                graph_complete_progress = instance_progress_start + (instance_weight * 0.15)
                self.queue.put(("progress", int(graph_complete_progress)))

                if self.stop_event.is_set():
                    self.queue.put(("log", ("Calculation stopped by user.", "warning")))
                    break

                # Start instance test
                self.queue.put(("phase", f"Optimizing {instance_name} instance ({n_nodes} nodes)"))
                self.queue.put(("log", (f"Starting optimization for {instance_name} instance...", "info")))

                # Progress information for the instance
                progress_info = {
                    "start_progress": graph_complete_progress,
                    "total_progress": instance_weight * 0.85,
                    "queue": self.queue
                }

                # Execute simulation for current instance
                try:
                    self.results[instance_name] = test_instance(
                        G, max_children, penalty,
                        instance_name=instance_name,
                        stop_event=self.stop_event,
                        queue=self.queue,
                        progress_info=progress_info
                    )
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.queue.put(("error", f"Error in optimization for {instance_name}: {e}"))
                    return

                # Update overall progress after instance completion
                overall_progress = instance_progress_start + instance_weight
                self.queue.put(("progress", int(overall_progress)))
                self.queue.put(("log", (f"Optimization for {instance_name} instance completed", "success")))

                if self.stop_event.is_set():
                    self.queue.put(("log", ("Calculation stopped by user.", "warning")))
                    break

            # Save final results
            plot_dir = get_current_plot_directory()
            self.save_results(instances, self.max_children.get(), self.penalty.get(), self.results, plot_dir)
            self.queue.put(("log", ("Optimization completed.", "success")))
            self.queue.put(("progress", 100))

            # Keep progress bar at 100% for 3 seconds then reset
            self.root.after(3000, self.reset_progress_bar)

        except Exception as e:
            self.queue.put(("error", f"Error during optimization: {str(e)}"))
            logging.error(f"Error in optimization: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def save_results(self, instances, max_children, penalty, results, plot_dir):
        """
        Save graph images and comparison tables for all instances.

        Args:
            instances (dict): Dictionary with instance names and number of nodes.
            max_children (int): Maximum number of children allowed.
            penalty (int): Penalty applied for degree constraint violations.
            results (dict): Optimization results for each instance.
            plot_dir (str): Directory where to save images and tables.
        """
        try:
            os.makedirs(plot_dir, exist_ok=True)

            # Calculate total number of images to create to update progress bar
            total_images = 0
            for size_name, instance_results in results.items():
                # Initial graph
                if "graph" in instance_results:
                    total_images += 1

                # Algorithm trees
                for algo in ["greedy", "local", "sa"]:
                    tree_key = f"{algo}_tree"
                    if tree_key in instance_results:
                        total_images += 1

            # Add 1 for each comparison table
            total_images += 1

            # Set initial progress for image creation
            # Use the last 10% of progress bar for image creation
            start_progress = 90
            current_progress = start_progress
            progress_increment = 10 / total_images if total_images > 0 else 0

            self.queue.put(("phase", "Creating and saving images"))
            self.queue.put(("progress", int(current_progress)))

            # Parameters to include in file names
            # Make k (max_children) value explicit in file name
            if self.advanced_mode.get():
                params_suffix = f"_k{max_children}_adv_pen{penalty}"
            else:
                multiplier = self.p_multiplier.get()
                params_suffix = f"_k{max_children}_mult{multiplier:.1f}x_pen{penalty}"

            # Mapping for extended size names
            dim_labels = {
                "small": "Small",
                "medium": "Medium",
                "large": "Large"
            }

            # 🚀 PERFORMANCE IMPROVEMENT: Batch image generation using parallel processing
            self.queue.put(("status", "Preparing batch image generation..."))
            self.queue.put(("log", ("🚀 Using parallel image generation to improve performance", "info")))

            # Prepare all image generation tasks
            image_tasks = []
            image_descriptions = []

            for size_name, instance_results in results.items():
                dim_label = dim_labels.get(size_name, size_name)

                # Graph images
                if "graph" in instance_results:
                    graph_filename = os.path.join(plot_dir, f"initial_graph_instance{dim_label}_{size_name}_n{instances[size_name]}{params_suffix}.png")
                    task = (draw_and_save_graph,
                           (instance_results["graph"], graph_filename),
                           {"max_children": max_children, "is_spanning_tree": False})
                    image_tasks.append(task)
                    image_descriptions.append(f"Graph {dim_label} ({size_name})")

                # Tree images for each algorithm
                for algo in ["greedy", "local", "sa"]:
                    tree_key = f"{algo}_tree"
                    if tree_key in instance_results:
                        algo_labels = {"greedy": "Greedy", "local": "LocalSearch", "sa": "SimulatedAnnealing"}
                        tree_filename = os.path.join(plot_dir, f"tree_{algo_labels[algo]}_instance{dim_label}_{size_name}_n{instances[size_name]}{params_suffix}.png")
                        task = (draw_and_save_graph,
                               (instance_results[tree_key], tree_filename),
                               {"max_children": max_children, "is_spanning_tree": True})
                        image_tasks.append(task)
                        algo_name = {"greedy": "Greedy", "local": "Local Search", "sa": "Simulated Annealing"}
                        image_descriptions.append(f"Tree {algo_name[algo]} {dim_label} ({size_name})")

            # Execute batch image generation with progress tracking
            if image_tasks:
                self.queue.put(("log", (f"🎨 Generating {len(image_tasks)} images in parallel...", "info")))

                def image_progress_callback(completed, total):
                    progress_pct = (completed / total) * (progress_increment * len(image_tasks))
                    current_progress = start_progress + progress_pct
                    self.queue.put(("progress", int(current_progress)))
                    if completed <= len(image_descriptions):
                        desc = image_descriptions[completed-1] if completed > 0 else "Image"
                        self.queue.put(("status", f"Completed: {desc} ({completed}/{total})"))
                        self.queue.put(("log", (f"✅ {desc} generated ({completed}/{total})", "success")))

                # Use batch generation for improved performance
                results_batch = batch_generate_images(image_tasks, image_progress_callback)

                successful_images = sum(1 for result in results_batch if result)
                self.queue.put(("log", (f"🎉 Image generation completed: {successful_images}/{len(image_tasks)} successes", "success")))

                # Update image count for subsequent progress calculations
                image_count = len(image_tasks)

            # Also save comparison tables
            self.queue.put(("status", "Creating comparison table..."))
            self.queue.put(("log", ("Preparing comparison table...", "info")))
            table_data = []
            for size_name, metrics in results.items():
                dim_label = dim_labels.get(size_name, size_name)
                for algo in ["greedy", "local", "sa"]:
                    algo_key = f"{algo}_cost"
                    if algo_key in metrics:

                        calls = metrics.get(f"{algo}_calls", 0)
                        iterations = metrics.get(f"{algo}_iterations", calls)

                        # OPTIMIZATION: For SA, show only calls. For other algorithms, show calls with iterations
                        calls_display = calls
                        if algo == "sa":
                            # For SA, show only the number of calls (no iterations)
                            calls_display = calls
                        elif (algo == "local" and "local_iterations" in metrics) or (algo == "greedy" and "greedy_iterations" in metrics):
                            # For Local Search and Greedy, show calls with iterations if available
                            calls_display = f"{calls} ({iterations} iter.)"

                        # Add rows to the table
                        row = {
                            "Instance": f"{dim_label} ({size_name})",
                            "Algorithm": algo.capitalize(),
                            "Cost": metrics[algo_key],
                            "Time (s)": self.format_time(metrics[f"{algo}_time"]),
                            "Calls": calls_display,
                            "Memory (KB)": round(metrics[f"{algo}_memory"], 2),
                            "Violations": metrics.get(f"{algo}_violations", 0)
                        }

                        table_data.append(row)

            # Calculate scores after collecting all data
            if table_data:
                # Import evaluation function
                from .algorithms import evaluate_solution

                # Calculate maximum values for normalization
                max_cost = max(row["Cost"] for row in table_data)
                max_time = max(float(str(row["Time (s)"]).replace("e", "E")) if "e" in str(row["Time (s)"]) else float(row["Time (s)"]) for row in table_data)
                max_memory = max(row["Memory (KB)"] for row in table_data)
                max_violations = max(row["Violations"] for row in table_data)

                reference_values = {
                    "max_cost": max_cost,
                    "max_time": max_time,
                    "max_memory": max_memory,
                    "max_violations": max_violations
                }

                # Calculate score for each row
                for row in table_data:
                    time_value = float(str(row["Time (s)"]).replace("e", "E")) if "e" in str(row["Time (s)"]) else float(row["Time (s)"])
                    solution_data = {
                        "cost": row["Cost"],
                        "execution_time": time_value,
                        "memory": row["Memory (KB)"],
                        "violations": row["Violations"]
                    }

                    score = evaluate_solution(solution_data, reference_values)
                    row["Score"] = score

            if table_data:
                df = pd.DataFrame(table_data)

                # Find and highlight the best solution
                best_solution = df.loc[df["Score"].idxmax()]
                self.queue.put(("log", ("🏆 BEST SOLUTION FOUND:", "highlight")))
                self.queue.put(("log", (f"{best_solution['Instance']} - {best_solution['Algorithm']}: "
                                      f"Score={best_solution['Score']}, Cost={best_solution['Cost']}, "
                                      f"Violations={best_solution['Violations']}, Time={best_solution['Time (s)']}", "success")))

                # Load the complete comparison table in logs
                self.queue.put(("log", ("Complete results table:", "highlight")))
                for _, row in df.iterrows():
                    self.queue.put(("log", (f"{row['Instance']} - {row['Algorithm']}: Score={row['Score']}, "
                                          f"Cost={row['Cost']}, Violations={row['Violations']}, "
                                          f"Time={row['Time (s)']}, Calls={row['Calls']}, "
                                          f"Memory={row['Memory (KB)']} KB", "performance")))

                # 🚀 PERFORMANCE IMPROVEMENT: Async table generation
                table_filename = os.path.join(plot_dir, f"comparison_table{params_suffix}.png")
                self.queue.put(("status", "Generating comparison table..."))
                table_future = save_table_as_image(df, table_filename, async_mode=True)

                # Wait for table generation to complete
                try:
                    table_result = table_future.result(timeout=30)  # 30 second timeout
                    if table_result:
                        self.queue.put(("log", (f"📊 Comparison table saved: {table_filename}", "success")))
                    else:
                        self.queue.put(("log", ("⚠️ Error in table generation", "warning")))
                except Exception as e:
                    self.queue.put(("log", (f"❌ Error in table generation: {e}", "error")))

                # Update progress for the last image
                image_count += 1
                current_progress = start_progress + (image_count * progress_increment)
                self.queue.put(("progress", int(current_progress)))

            # Generate temporal graphs of score evolution for each instance
            self.queue.put(("status", "Generating score evolution graphs..."))
            self.queue.put(("log", ("Creating temporal score evolution graphs...", "info")))

            from .utils import plot_score_evolution

            for size_name, instance_results in results.items():
                # Collect score histories for this instance
                score_histories = {}

                if "local_score_history" in instance_results and instance_results["local_score_history"]:
                    score_histories["Local Search"] = instance_results["local_score_history"]

                if "sa_score_history" in instance_results and instance_results["sa_score_history"]:
                    score_histories["Simulated Annealing"] = instance_results["sa_score_history"]

                # Generate graph only if there is data
                if score_histories:
                    # Calculate final reference values for normalization
                    all_costs = []
                    all_times = []
                    all_memories = []
                    all_violations = []

                    # Collect all final values from algorithms
                    for algo in ["greedy", "local", "sa"]:
                        if f"{algo}_cost" in instance_results:
                            all_costs.append(instance_results[f"{algo}_cost"])
                        if f"{algo}_time" in instance_results:
                            all_times.append(instance_results[f"{algo}_time"])
                        if f"{algo}_memory" in instance_results:
                            all_memories.append(instance_results[f"{algo}_memory"])
                        if f"{algo}_violations" in instance_results:
                            all_violations.append(instance_results[f"{algo}_violations"])

                    # Calculate final reference values
                    reference_final_values = {
                        "max_cost": max(all_costs) if all_costs else 1,
                        "max_time": max(all_times) if all_times else 1,
                        "max_memory": max(all_memories) if all_memories else 1,
                        "max_violations": max(all_violations) if all_violations else 1
                    }

                    dim_label = dim_labels.get(size_name, size_name)
                    evolution_filename = f"score_evolution_instance{dim_label}_{size_name}_n{instances[size_name]}{params_suffix}.png"

                    self.queue.put(("log", (f"Creating evolution graph for {dim_label} instance ({size_name})...", "info")))
                    success = plot_score_evolution(score_histories, reference_final_values, evolution_filename)

                    if success:
                        self.queue.put(("log", (f"Evolution graph for {dim_label} instance ({size_name}) saved", "success")))
                    else:
                        self.queue.put(("log", (f"Error creating evolution graph for {dim_label} instance ({size_name})", "error")))

            self.queue.put(("status", "All images created successfully"))
            self.queue.put(("progress", 100))  # Ensure progress bar reaches 100%
            self.queue.put(("log", ("Results saved successfully.", "success")))

        except Exception as e:
            logging.error(f"Error saving results: {e}")
            self.queue.put(("log", (f"Error saving results: {e}", "error")))
        finally:
            # 🧹 PERFORMANCE IMPROVEMENT: Cleanup resources
            clear_image_cache()
            _cleanup_image_thread_pool()

    # Configuration Management Methods
    def get_current_configuration(self):
        """Get current GUI configuration as a dictionary."""
        config = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "n_small": self.n_small.get(),
                "n_medium": self.n_medium.get(),
                "n_large": self.n_large.get(),
                "max_children": self.max_children.get(),
                "penalty": self.penalty.get(),
                "p_multiplier": self.p_multiplier.get(),
                "advanced_mode": self.advanced_mode.get(),
                "p_small_base": self.p_small_base.get(),
                "p_medium_base": self.p_medium_base.get(),
                "p_large_base": self.p_large_base.get()
            }
        }
        return config

    def apply_configuration(self, config):
        """Apply configuration to GUI elements."""
        try:
            params = config.get("parameters", {})

            # Apply basic parameters
            self.n_small.set(params.get("n_small", 10))
            self.n_medium.set(params.get("n_medium", 50))
            self.n_large.set(params.get("n_large", 200))
            self.max_children.set(params.get("max_children", 3))
            self.penalty.set(params.get("penalty", 1000))
            self.p_multiplier.set(params.get("p_multiplier", 1.0))

            # Apply advanced mode settings
            self.advanced_mode.set(params.get("advanced_mode", False))
            self.p_small_base.set(params.get("p_small_base", 0.4))
            self.p_medium_base.set(params.get("p_medium_base", 0.3))
            self.p_large_base.set(params.get("p_large_base", 0.15))

            # Update GUI state
            self.toggle_advanced_mode()
            self.on_multiplier_change(self.p_multiplier.get())

            return True
        except Exception as e:
            logging.error(f"Error applying configuration: {e}")
            return False

    def export_configuration(self):
        """Export current configuration to a shareable location."""
        try:
            # Default to Desktop for easy sharing
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"dcst_config_export_{timestamp}.json"

            filename = filedialog.asksaveasfilename(
                title="Export Configuration",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir=desktop_path,
                initialfile=default_filename
            )

            if filename:
                config = self.get_current_configuration()
                config["name"] = f"Exported_{os.path.splitext(os.path.basename(filename))[0]}"
                config["exported"] = True
                config["export_timestamp"] = datetime.now().isoformat()

                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)

                messagebox.showinfo("Success", f"Configuration exported successfully to:\n{filename}")
                self.log_message(f"Configuration exported: {filename}", "success")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export configuration:\n{str(e)}")
            self.log_message(f"Error exporting configuration: {e}", "error")

    def import_configuration(self):
        """Import configuration from an external file."""
        try:
            filename = filedialog.askopenfilename(
                title="Import Configuration",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir=os.path.expanduser("~")
            )

            if filename:
                with open(filename, 'r') as f:
                    config = json.load(f)

                # Validate configuration
                if not self.validate_configuration(config):
                    messagebox.showerror("Error", "Invalid configuration file format")
                    return

                if self.apply_configuration(config):
                    messagebox.showinfo("Success", f"Configuration imported successfully from:\n{filename}")
                    self.log_message(f"Configuration imported: {filename}", "success")
                else:
                    messagebox.showerror("Error", "Failed to apply imported configuration")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to import configuration:\n{str(e)}")
            self.log_message(f"Error importing configuration: {e}", "error")

    def validate_configuration(self, config):
        """Validate configuration file format."""
        try:
            if not isinstance(config, dict):
                return False

            params = config.get("parameters", {})
            if not isinstance(params, dict):
                return False

            # Check for required parameters
            required_params = ["n_small", "n_medium", "n_large", "max_children", "penalty"]
            for param in required_params:
                if param not in params:
                    return False

            return True
        except:
            return False

    def format_time(self, time_value):
        """
        Format a time value in seconds to a string with appropriate precision.
        For small values (< 0.1), use scientific notation.
        For medium values (< 1), round to 4th decimal place.
        For larger values, round to 2 decimal places.
        """
        if time_value < 0.1:
            return f"{time_value:.4e}"
        elif time_value < 1:
            return f"{time_value:.4f}"
        else:
            return f"{time_value:.2f}"

if __name__ == "__main__":
    root = tk.Tk()
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    app = App(root, progress_bar)
    root.mainloop()
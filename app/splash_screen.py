#!/usr/bin/env python3
"""
Splash screen implementation for DCST Tool.
Displays during application startup to provide visual feedback.
Fixed threading and event loop management for proper startup sequence.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import sys
import logging
from PIL import Image, ImageTk
import platform

class SplashScreen:
    """
    A splash screen that displays during application startup.
    Shows branding, loading progress, and initialization status.

    Fixed implementation with proper thread management and event loop handling.
    """

    def __init__(self, parent_root=None, duration=3.0):
        """
        Initialize the splash screen.

        Args:
            parent_root (tk.Tk, optional): Parent root window to use
            duration (float): Minimum time to show splash screen in seconds
        """
        self.duration = duration
        self.parent_root = parent_root
        self.splash_root = None
        self.progress_var = None
        self.status_var = None
        self.start_time = time.time()
        self.is_closed = False
        self.animation_thread = None
        self.manual_mode = False  # Flag to disable automatic animation
        
    def create_splash(self):
        """Create and display the splash screen."""
        if self.parent_root:
            # Use Toplevel if parent root exists
            self.splash_root = tk.Toplevel(self.parent_root)
        else:
            # Create new root if no parent (fallback)
            self.splash_root = tk.Tk()

        self.splash_root.title("DCST Tool")
        
        # Configure splash window
        splash_width = 500
        splash_height = 350
        
        # Center the splash screen
        screen_width = self.splash_root.winfo_screenwidth()
        screen_height = self.splash_root.winfo_screenheight()
        x = (screen_width - splash_width) // 2
        y = (screen_height - splash_height) // 2
        
        self.splash_root.geometry(f"{splash_width}x{splash_height}+{x}+{y}")
        self.splash_root.resizable(False, False)
        
        # Remove window decorations for a cleaner look
        self.splash_root.overrideredirect(True)
        
        # Set icon if available
        self._set_splash_icon()
        
        # Configure colors based on platform
        if platform.system() == "Darwin":  # macOS
            bg_color = "#f0f0f0"
            text_color = "#333333"
            accent_color = "#007AFF"
        else:  # Windows and Linux
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            accent_color = "#0078d4"
        
        self.splash_root.configure(bg=bg_color)
        
        # Create main frame
        main_frame = tk.Frame(self.splash_root, bg=bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Application title
        title_label = tk.Label(
            main_frame,
            text="DCST Tool",
            font=("Arial", 24, "bold"),
            fg=accent_color,
            bg=bg_color
        )
        title_label.pack(pady=(20, 5))
        
        # Subtitle
        subtitle_label = tk.Label(
            main_frame,
            text="Degree-Constrained Spanning Tree Tool",
            font=("Arial", 12),
            fg=text_color,
            bg=bg_color
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Algorithm list
        algorithms_frame = tk.Frame(main_frame, bg=bg_color)
        algorithms_frame.pack(pady=10)
        
        algorithms = [
            "• Modified Kruskal's Algorithm (Greedy)",
            "• Hill Climbing (First Improvement)",
            "• Simulated Annealing with Edge Swapping"
        ]
        
        for algo in algorithms:
            algo_label = tk.Label(
                algorithms_frame,
                text=algo,
                font=("Arial", 10),
                fg=text_color,
                bg=bg_color,
                anchor="w"
            )
            algo_label.pack(anchor="w", pady=2)
        
        # Progress bar
        progress_frame = tk.Frame(main_frame, bg=bg_color)
        progress_frame.pack(fill="x", pady=(30, 10))
        
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode="determinate"
        )
        progress_bar.pack()
        
        # Status label
        self.status_var = tk.StringVar(value="Initializing...")
        status_label = tk.Label(
            main_frame,
            textvariable=self.status_var,
            font=("Arial", 10),
            fg=text_color,
            bg=bg_color
        )
        status_label.pack(pady=(5, 20))
        
        # Version info
        version_label = tk.Label(
            main_frame,
            text="Version 1.0.0 • Cross-Platform",
            font=("Arial", 8),
            fg=text_color,
            bg=bg_color
        )
        version_label.pack(side="bottom", pady=(0, 10))
        
        # Make splash screen stay on top
        self.splash_root.attributes("-topmost", True)

        # Start progress animation only if not in manual mode
        if not self.manual_mode:
            self._animate_progress()

        return self.splash_root
    
    def _set_splash_icon(self):
        """Set the splash screen icon."""
        try:
            # Try to find icon file
            icon_paths = [
                "icon.ico",
                os.path.join(os.path.dirname(__file__), "..", "icon.ico"),
                os.path.join(os.path.dirname(sys.executable), "icon.ico")
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        if platform.system() == "Windows":
                            self.splash_root.iconbitmap(icon_path)
                        else:
                            # For macOS and Linux, try to load as PhotoImage
                            try:
                                # Convert ICO to PhotoImage if PIL is available
                                img = Image.open(icon_path)
                                img = img.resize((32, 32), Image.Resampling.LANCZOS)
                                photo = ImageTk.PhotoImage(img)
                                self.splash_root.iconphoto(True, photo)
                            except:
                                # Fallback for systems without PIL
                                pass
                        break
                    except Exception as e:
                        continue
        except Exception:
            pass  # Icon setting is optional
    
    def _animate_progress(self):
        """Animate the progress bar during loading (automatic mode only)."""
        def update_progress():
            steps = [
                (20, "Loading dependencies..."),
                (40, "Initializing algorithms..."),
                (60, "Setting up GUI components..."),
                (80, "Configuring system resources..."),
                (100, "Ready!")
            ]

            for progress, status in steps:
                if self.is_closed or self.manual_mode:
                    break

                try:
                    # Use after to ensure thread safety - create proper closure
                    def update_func(p=progress, s=status):
                        return self._update_progress_safe(p, s)

                    self.splash_root.after(0, update_func)
                    time.sleep(0.5)
                except Exception as e:
                    logging.warning(f"Progress animation error: {e}")
                    break

            # Ensure minimum display time
            elapsed = time.time() - self.start_time
            if elapsed < self.duration and not self.manual_mode:
                remaining = self.duration - elapsed
                time.sleep(remaining)

        # Run progress animation in a separate thread
        self.animation_thread = threading.Thread(target=update_progress, daemon=True)
        self.animation_thread.start()

    def _update_progress_safe(self, progress, status):
        """Thread-safe progress update."""
        try:
            if not self.is_closed and self.splash_root and self.progress_var and self.status_var:
                if progress is not None:
                    self.progress_var.set(progress)
                if status is not None:
                    self.status_var.set(status)
                self.splash_root.update_idletasks()
        except Exception as e:
            logging.warning(f"Progress update error: {e}")
    
    def update_status(self, status, progress=None):
        """
        Update the splash screen status (thread-safe).

        Args:
            status (str): Status message to display
            progress (float, optional): Progress percentage (0-100)
        """
        if self.is_closed or not self.splash_root:
            return

        # Enable manual mode to prevent conflicts with automatic animation
        self.manual_mode = True

        try:
            # Use after to ensure thread safety - create proper closure
            def update_func():
                return self._update_progress_safe(progress, status)

            self.splash_root.after(0, update_func)
        except Exception as e:
            logging.warning(f"Status update error: {e}")

    def enable_manual_mode(self):
        """Enable manual mode to disable automatic animation."""
        self.manual_mode = True
    
    def close(self):
        """Close the splash screen safely."""
        if self.splash_root and not self.is_closed:
            self.is_closed = True
            self.manual_mode = True  # Stop any ongoing animations

            try:
                # Wait for animation thread to finish
                if self.animation_thread and self.animation_thread.is_alive():
                    self.animation_thread.join(timeout=1.0)

                # Destroy the splash window
                self.splash_root.destroy()
                logging.info("Splash screen closed successfully")
            except Exception as e:
                logging.warning(f"Error closing splash screen: {e}")
            finally:
                self.splash_root = None

def show_splash_screen(parent_root=None, duration=3.0, manual_mode=False):
    """
    Show a splash screen for the specified duration.

    Args:
        parent_root (tk.Tk, optional): Parent root window to use
        duration (float): Minimum time to show splash screen
        manual_mode (bool): If True, disable automatic animation

    Returns:
        SplashScreen: The splash screen instance
    """
    try:
        splash = SplashScreen(parent_root=parent_root, duration=duration)

        if manual_mode:
            splash.enable_manual_mode()

        splash_window = splash.create_splash()

        # Process events to show the splash screen
        splash_window.update_idletasks()
        splash_window.update()

        logging.info("Splash screen created successfully")
        return splash

    except Exception as e:
        logging.error(f"Failed to create splash screen: {e}")
        return None

if __name__ == "__main__":
    # Test the splash screen
    logging.basicConfig(level=logging.INFO)

    # Create a test root
    test_root = tk.Tk()
    test_root.withdraw()

    splash = show_splash_screen(parent_root=test_root, duration=5.0, manual_mode=True)

    if splash:
        # Simulate some loading
        time.sleep(1)
        splash.update_status("Testing splash screen...", 50)
        time.sleep(2)
        splash.update_status("Almost ready...", 90)
        time.sleep(1)
        splash.update_status("Ready!", 100)
        time.sleep(1)

        splash.close()

    test_root.destroy()

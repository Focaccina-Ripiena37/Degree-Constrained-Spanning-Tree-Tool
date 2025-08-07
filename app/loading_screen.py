#!/usr/bin/env python3
"""
DCST Tool - Loading Screen Module
Provides a fast-loading splash screen that displays while the main application initializes.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import sys

class LoadingScreen:
    """Fast-loading splash screen for DCST Tool."""
    
    def __init__(self):
        self.splash_root = None
        self.progress_var = None
        self.status_var = None
        self.is_closed = False
        self._lock = threading.Lock()
        
    def create_splash(self):
        """Create and display the splash screen."""
        try:
            # Create splash window
            self.splash_root = tk.Tk()
            self.splash_root.title("DCST Tool")
            
            # Configure splash window
            self.splash_root.overrideredirect(True)  # Remove window decorations
            self.splash_root.configure(bg='#2b2b2b')
            
            # Set window size and center it
            width, height = 400, 250
            screen_width = self.splash_root.winfo_screenwidth()
            screen_height = self.splash_root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.splash_root.geometry(f"{width}x{height}+{x}+{y}")
            
            # Make splash stay on top
            self.splash_root.attributes("-topmost", True)
            
            # Create main frame
            main_frame = tk.Frame(self.splash_root, bg='#2b2b2b', padx=30, pady=30)
            main_frame.pack(fill="both", expand=True)
            
            # Title
            title_label = tk.Label(
                main_frame,
                text="DCST Tool",
                font=("Arial", 20, "bold"),
                fg='#ffffff',
                bg='#2b2b2b'
            )
            title_label.pack(pady=(0, 10))
            
            # Subtitle
            subtitle_label = tk.Label(
                main_frame,
                text="Degree-Constrained Spanning Tree Optimization",
                font=("Arial", 10),
                fg='#cccccc',
                bg='#2b2b2b'
            )
            subtitle_label.pack(pady=(0, 20))
            
            # Progress bar
            self.progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(
                main_frame,
                variable=self.progress_var,
                maximum=100,
                length=300,
                mode='determinate'
            )
            progress_bar.pack(pady=(0, 10))
            
            # Status label
            self.status_var = tk.StringVar(value="Initializing...")
            status_label = tk.Label(
                main_frame,
                textvariable=self.status_var,
                font=("Arial", 9),
                fg='#cccccc',
                bg='#2b2b2b'
            )
            status_label.pack(pady=(0, 15))
            
            # Version info
            version_label = tk.Label(
                main_frame,
                text="Version 1.0.0 • University of Ferrara",
                font=("Arial", 8),
                fg='#888888',
                bg='#2b2b2b'
            )
            version_label.pack(side="bottom")
            
            # Don't start automatic animation - will be controlled manually
            return self.splash_root
            
        except Exception as e:
            print(f"Error creating splash screen: {e}")
            return None
    
    # Removed automatic animation - progress controlled manually
    
    def update_progress(self, progress, status=None):
        """Update progress bar and status."""
        with self._lock:
            if self.is_closed or not self.splash_root:
                return
                
            try:
                self.progress_var.set(progress)
                if status:
                    self.status_var.set(status)
                self.splash_root.update_idletasks()
            except Exception:
                pass  # Ignore errors during update
    
    def close(self):
        """Close the splash screen immediately."""
        with self._lock:
            if self.is_closed or not self.splash_root:
                return

            try:
                self.is_closed = True
                self.progress_var.set(100)
                self.status_var.set("Ready!")
                self.splash_root.update_idletasks()

                # Destroy immediately for faster transition
                self._destroy_splash()

            except Exception:
                self._destroy_splash()

    def _destroy_splash(self):
        """Destroy the splash window."""
        try:
            if self.splash_root:
                # Withdraw window first to hide it immediately
                self.splash_root.withdraw()
                # Update to process the withdraw
                self.splash_root.update_idletasks()
                # Then destroy
                self.splash_root.destroy()
                self.splash_root = None
        except Exception:
            pass  # Ignore errors during destruction

# Global splash screen instance
_splash_screen = None

def show_loading_screen():
    """Show the loading screen."""
    global _splash_screen
    try:
        _splash_screen = LoadingScreen()
        splash_root = _splash_screen.create_splash()
        return _splash_screen, splash_root
    except Exception as e:
        print(f"Failed to create loading screen: {e}")
        return None, None

def update_loading_progress(progress, status=None):
    """Update loading screen progress."""
    global _splash_screen
    if _splash_screen:
        _splash_screen.update_progress(progress, status)

def close_loading_screen():
    """Close the loading screen."""
    global _splash_screen
    if _splash_screen:
        _splash_screen.close()
        _splash_screen = None

def run_loading_screen_loop(splash_root):
    """Run the loading screen event loop."""
    if splash_root:
        try:
            splash_root.mainloop()
        except Exception:
            pass  # Ignore errors in splash screen loop

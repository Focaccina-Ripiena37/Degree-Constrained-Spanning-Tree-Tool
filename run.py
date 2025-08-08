#!/usr/bin/env python3
"""
DCST Tool - Optimized startup sequence with lazy loading
Includes performance optimizations and loading screen support.
"""

import os
import sys
import platform
import multiprocessing
import time
import logging
import threading

# Configure minimal logging to reduce startup overhead
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

# NumPy PyInstaller compatibility fixes - optimized
def fix_numpy_pyinstaller():
    """Apply NumPy fixes for PyInstaller compatibility."""
    # Set environment variables before any NumPy imports
    os.environ.update({
        'NUMPY_EXPERIMENTAL_ARRAY_FUNCTION': '0',
        'OPENBLAS_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'OMP_NUM_THREADS': '1',
        'NPY_NUM_BUILD_JOBS': '1'
    })

    # Disable NumPy warnings that can cause issues in PyInstaller
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy')
    warnings.filterwarnings('ignore', message='.*CPU dispatcher.*')

# Apply NumPy fixes before any other imports
fix_numpy_pyinstaller()

# Lazy import variables - will be loaded when needed
_tkinter_loaded = False
_app_modules_loaded = False

# Import loading screen at module level for immediate availability
try:
    # from app.loading_screen import LoadingScreen
    from app.splash_screen import show_splash_screen
    _loading_screen_available = True
except ImportError:
    _loading_screen_available = False

def lazy_load_tkinter():
    """Lazy load tkinter modules."""
    global _tkinter_loaded
    if not _tkinter_loaded:
        global tk, ttk
        import tkinter as tk
        from tkinter import ttk
        _tkinter_loaded = True
    return tk, ttk

def lazy_load_app_modules():
    """Lazy load app modules."""
    global _app_modules_loaded
    if not _app_modules_loaded:
        global App
        from app.gui import App
        _app_modules_loaded = True
    return App

def configure_cpu_optimization():
    """Configure CPU optimization for the application."""
    try:
        # Set multiprocessing start method for compatibility
        if hasattr(multiprocessing, 'set_start_method'):
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except RuntimeError:
                pass  # Already set

        # Get CPU count
        cpu_count = multiprocessing.cpu_count()

        # Conservative approach for stability
        max_workers = min(cpu_count, 4)  # Limit to 4 cores max

        return max_workers

    except Exception as e:
        return 2  # Safe fallback

def set_application_icon(root):
    """Set the application icon for the main window."""
    try:
        # Ensure window is properly initialized before setting icon
        root.update_idletasks()

        icon_paths = [
            "icon.ico",
            os.path.join(os.path.dirname(__file__), "icon.ico"),
            os.path.join(os.path.dirname(sys.executable), "icon.ico"),
            os.path.join(os.path.dirname(sys.executable), "app", "icon.ico")
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    # Try different methods based on platform
                    if platform.system() == "Windows":
                        root.iconbitmap(default=icon_path)
                    else:
                        # For macOS and Linux, try iconbitmap without default parameter
                        root.iconbitmap(icon_path)
                    return True
                except Exception:
                    # Silently continue to next path
                    continue

        # If no icon found, that's okay - just continue without icon
        return False
    except Exception:
        # Silently fail if icon loading fails
        return False

def initialize_application_fast(root=None):
    """Initialize the main application with optimized startup.

    If a Tk root is provided, reuse it to avoid creating multiple Tk instances.
    """
    try:
        # Configure CPU optimization (minimal overhead)
        cpu_count = configure_cpu_optimization()

        # Lazy load tkinter
        tk, ttk = lazy_load_tkinter()

        # Create or reuse main window (avoid multiple Tk roots)
        if root is None:
            root = tk.Tk()
            root.withdraw()  # Hide initially for faster startup
        else:
            # Ensure it's hidden during setup
            try:
                root.withdraw()
            except Exception:
                pass

        # Set basic title (detailed system info will be loaded later)
        root.title("DCST Tool - Loading...")

        # Set application icon (non-blocking)
        set_application_icon(root)

        # Lazy load app modules
        App = lazy_load_app_modules()

        # Create progress bar and app
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        app = App(root, progress_bar)

        # Load system info in background (non-blocking)
        def load_system_info():
            try:
                from app.algorithms import detect_system_resources, classify_system_type, check_user_overrides
                cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()
                system_type, safety_margin, ram_efficiency = classify_system_type(cpu_cores, available_ram_gb)
                user_overrides = check_user_overrides()

                if user_overrides['force_conservative']:
                    title_suffix = "CONSERVATIVE MODE"
                elif system_type == "workstation":
                    title_suffix = f"WORKSTATION MODE ({cpu_cores} cores)"
                elif system_type == "desktop":
                    title_suffix = f"DESKTOP MODE ({cpu_cores} cores)"
                else:
                    title_suffix = f"LAPTOP MODE ({cpu_cores} cores)"

                # Update title when ready
                root.title(f"DCST Tool - {title_suffix}")

            except Exception:
                root.title(f"DCST Tool - SAFE MODE ({cpu_count} cores)")

        # Schedule system info loading after main window is shown
        root.after(100, load_system_info)

        return root, app

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, None

def main():
    """Main application entry point with immediate loading screen."""
    splash = None
    main_root = None

    try:
        # Ensure tkinter is loaded and create ONE root
        tk, _ttk = lazy_load_tkinter()
        main_root = tk.Tk()
        main_root.withdraw()

        # Create and show loading screen immediately using the same root
        if _loading_screen_available:
            splash = show_splash_screen(parent_root=main_root, duration=3.0, manual_mode=True)
            splash_root = splash.splash_root if splash else None
        else:
            splash_root = None

        if not splash_root:
            # Fallback to direct startup if splash fails
            return main_without_splash()

        # Update splash screen and process events to make it visible immediately
        splash.update_status("Starting DCST Tool...", 10)
        splash_root.update_idletasks()
        splash_root.update()

        # Initialize main application using the SAME root
        splash.update_status("Loading core modules...", 30)
        splash_root.update()

        result = initialize_application_fast(root=main_root)

        splash.update_status("Setting up interface...", 70)
        splash_root.update()

        if result and len(result) == 2:
            main_root, app = result

            splash.update_status("Finalizing...", 90)
            splash_root.update()

            # Prepare main window for display
            main_root.title("DCST Tool")  # Set final title

            # Close splash screen first
            splash.update_status("Ready!", 100)
            splash_root.update()
            time.sleep(0.1)

            # Destroy splash screen completely
            splash.close()
            time.sleep(0.1)

            # Show main application window
            main_root.deiconify()
            main_root.lift()
            main_root.focus_force()
            main_root.attributes('-topmost', True)  # Ensure it comes to front
            main_root.attributes('-topmost', False)  # Remove topmost after showing

            # Start the main event loop
            main_root.mainloop()

        else:
            if splash:
                splash.close()
            sys.exit(1)

    except KeyboardInterrupt:
        if splash:
            splash.close()
        if main_root:
            main_root.quit()
        sys.exit(0)

    except Exception as e:
        if splash:
            try:
                splash.close()
            except Exception:
                pass
        if main_root:
            try:
                main_root.quit()
            except Exception:
                pass
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main_without_splash():
    """Fallback main function without splash screen."""
    try:
        result = initialize_application_fast()
        if result and len(result) == 2:
            root, app = result
            root.deiconify()
            root.lift()
            root.focus_force()

            # Force window to be visible and on top
            root.attributes('-topmost', True)
            root.update()
            root.attributes('-topmost', False)

            root.mainloop()
        else:
            sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
DCST Tool - Simplified startup sequence with NumPy PyInstaller fixes
Eliminates complex splash screen logic that was causing hanging issues.
Includes fixes for NumPy CPU dispatcher conflicts in PyInstaller builds.
"""

import os
import sys
import platform
import multiprocessing
import time
import logging

# Configure logging to suppress warnings
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

# NumPy PyInstaller compatibility fixes
def fix_numpy_pyinstaller():
    """Apply NumPy fixes for PyInstaller compatibility."""
    # Set environment variables before any NumPy imports
    os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['NPY_NUM_BUILD_JOBS'] = '1'

    # Disable NumPy warnings that can cause issues in PyInstaller
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy')
    warnings.filterwarnings('ignore', message='.*CPU dispatcher.*')

# Apply NumPy fixes before any other imports
fix_numpy_pyinstaller()

# Now safe to import tkinter and app modules
import tkinter as tk
from tkinter import ttk

# Import app modules after NumPy fixes
from app.gui import App

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
        
        print(f"✅ CPU optimization configured: {max_workers}/{cpu_count} cores")
        return max_workers
        
    except Exception as e:
        print(f"⚠️ CPU optimization failed: {e}")
        return 2  # Safe fallback

def set_application_icon(root):
    """Set the application icon for the main window."""
    icon_paths = [
        "icon.ico",
        os.path.join(os.path.dirname(__file__), "icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "app", "icon.ico")
    ]
    
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            try:
                # Use iconbitmap for all platforms to avoid PIL issues
                root.iconbitmap(default=icon_path)
                return True
            except Exception:
                # Silently continue to next path
                continue
    
    # If no icon found, that's okay - just continue without icon
    return False

def show_loading_message():
    """Show a simple loading message in the console."""
    print("🚀 Starting DCST Tool...")
    print("📦 Loading components...")
    
def initialize_application():
    """Initialize the main application."""
    try:
        print("⚙️ Configuring system resources...")
        # Configure CPU optimization
        cpu_count = configure_cpu_optimization()

        print("🔍 Detecting system capabilities...")
        # Import and detect system resources
        try:
            from app.algorithms import detect_system_resources, classify_system_type, check_user_overrides

            cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()
            system_type, safety_margin, ram_efficiency = classify_system_type(cpu_cores, available_ram_gb)
            user_overrides = check_user_overrides()

            print(f"🖥️ System Classification: {system_type.upper()}")
            print(f"📊 Hardware: {cpu_cores} cores, {total_ram_gb:.1f}GB total RAM, {available_ram_gb:.1f}GB available")

            if user_overrides['force_conservative']:
                title_suffix = "CONSERVATIVE MODE"
            elif system_type == "workstation":
                title_suffix = f"WORKSTATION MODE ({cpu_cores} cores)"
            elif system_type == "desktop":
                title_suffix = f"DESKTOP MODE ({cpu_cores} cores)"
            else:
                title_suffix = f"LAPTOP MODE ({cpu_cores} cores)"

        except Exception as e:
            print(f"⚠️ Could not detect system classification: {e}")
            title_suffix = f"SAFE MODE ({cpu_count} cores)"

        print("🖥️ Creating main window...")
        # Create main window
        root = tk.Tk()
        root.title(f"DCST Tool - {title_suffix}")

        print("🎨 Setting up application icon...")
        # Set application icon
        icon_set = set_application_icon(root)
        if icon_set:
            print("✅ Application icon loaded successfully")
        else:
            print("⚠️ Could not load application icon (continuing without icon)")

        print("🔧 Initializing GUI components...")
        # Create progress bar and app
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        app = App(root, progress_bar)

        print("🚀 DCST Tool initialized successfully")
        return root, app, title_suffix
        
    except Exception as e:
        print(f"❌ Failed to initialize application: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def main():
    """Main application entry point with simplified startup."""
    try:
        # Show loading message
        show_loading_message()
        
        # Initialize application directly
        root, app, title_suffix = initialize_application()
        
        if root and app:
            print("✅ Launching main application window...")
            
            # Show main application window
            root.deiconify()
            root.lift()
            root.focus_force()
            
            print("✅ Starting main event loop...")
            print("📖 See documentation for usage instructions")
            
            # Start the main event loop
            root.mainloop()
            
        else:
            print("❌ Failed to initialize application")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        
        # Create crash log
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            crash_log_path = f"crash_log_{timestamp}.txt"
            
            with open(crash_log_path, "w") as f:
                f.write(f"DCST Tool Crash Log - {datetime.datetime.now()}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Error: {e}\n\n")
                f.write("Traceback:\n")
                traceback.print_exc(file=f)
                
                f.write(f"\nSystem Information:\n")
                f.write(f"Platform: {platform.system()} {platform.release()}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Architecture: {platform.machine()}\n")
            
            print(f"💥 Crash log saved to: {crash_log_path}")
            
        except Exception as log_error:
            print(f"💥 Could not save crash log: {log_error}")
        
        sys.exit(1)

if __name__ == "__main__":
    main()

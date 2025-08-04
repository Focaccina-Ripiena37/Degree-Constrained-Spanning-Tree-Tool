#!/usr/bin/env python3
"""
DCST Tool - Fixed startup sequence
Addresses threading and GUI initialization issues.
"""

from app.gui import App
import tkinter as tk
from tkinter import ttk
import os
import sys
import platform
import multiprocessing
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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
            except Exception as e:
                # Silently continue to next path
                continue

    # If no icon found, that's okay - just continue without icon
    return False

def show_simple_splash(parent_root):
    """Show a simple splash screen without threading complications."""
    try:
        # Create splash window as child of parent root
        splash = tk.Toplevel(parent_root)
        splash.title("DCST Tool")
        splash.geometry("400x300")
        splash.resizable(False, False)

        # Center the splash screen
        splash.update_idletasks()
        x = (splash.winfo_screenwidth() - 400) // 2
        y = (splash.winfo_screenheight() - 300) // 2
        splash.geometry(f"400x300+{x}+{y}")

        # Remove window decorations
        splash.overrideredirect(True)

        # Configure colors based on platform
        if platform.system() == "Darwin":  # macOS
            bg_color = "#f0f0f0"
            text_color = "#333333"
            accent_color = "#007AFF"
        else:  # Windows and Linux
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            accent_color = "#0078d4"

        splash.configure(bg=bg_color)

        # Create content
        main_frame = tk.Frame(splash, bg=bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(main_frame, text="DCST Tool",
                              font=("Arial", 20, "bold"),
                              fg=accent_color, bg=bg_color)
        title_label.pack(pady=(20, 10))

        # Subtitle
        subtitle_label = tk.Label(main_frame, text="Degree-Constrained Spanning Tree Tool",
                                 font=("Arial", 12), fg=text_color, bg=bg_color)
        subtitle_label.pack(pady=(0, 20))

        # Status label
        status_label = tk.Label(main_frame, text="Initializing...",
                               font=("Arial", 10), fg=text_color, bg=bg_color)
        status_label.pack(pady=(20, 10))

        # Progress bar
        progress = ttk.Progressbar(main_frame, length=300, mode="indeterminate")
        progress.pack(pady=10)
        progress.start()

        # Make splash stay on top
        splash.attributes("-topmost", True)
        splash.update()

        return splash, status_label, progress

    except Exception as e:
        logging.error(f"Failed to create splash screen: {e}")
        return None, None, None

def initialize_application():
    """Initialize the main application."""
    try:
        # Configure CPU optimization
        cpu_count = configure_cpu_optimization()

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
            logging.warning(f"Could not detect system classification: {e}")
            title_suffix = f"SAFE MODE ({cpu_count} cores)"

        # Create main window
        root = tk.Tk()
        root.title(f"DCST Tool - {title_suffix}")
        root.withdraw()  # Hide initially

        # Set application icon
        icon_set = set_application_icon(root)
        if icon_set:
            print("✅ Application icon loaded successfully")
        else:
            print("⚠️ Could not load application icon")

        # Create progress bar and app
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        app = App(root, progress_bar)

        print("🚀 DCST Tool initialized successfully")
        return root, app, title_suffix
        
    except Exception as e:
        logging.error(f"Failed to initialize application: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def main():
    """Main application entry point with improved error handling."""
    splash = None
    status_label = None
    progress = None
    main_root = None

    try:
        print("🚀 Starting DCST Tool...")

        # Create main root window
        main_root = tk.Tk()
        main_root.withdraw()

        # Show simple splash screen with proper parent
        splash, status_label, progress = show_simple_splash(main_root)

        if splash and status_label:
            status_label.config(text="Loading components...")
            splash.update()
            time.sleep(0.5)

        # Initialize application
        print("🔧 Initializing application components...")
        app_root, app, title_suffix = initialize_application()

        if app_root and app:
            if splash and status_label:
                status_label.config(text="Ready!")
                splash.update()
                time.sleep(0.5)

            # Close splash screen
            if splash:
                if progress:
                    progress.stop()  # Stop the progress bar animation
                splash.destroy()
                print("✅ Splash screen closed")

            # Destroy the temporary root
            if main_root:
                main_root.destroy()
                print("✅ Temporary root destroyed")

            # Show main application
            print("✅ Launching main application window...")
            app_root.deiconify()
            app_root.lift()
            app_root.focus_force()

            # Start the main event loop
            print("✅ Starting main event loop...")
            app_root.mainloop()

        else:
            print("❌ Failed to initialize application")
            if splash:
                if progress:
                    progress.stop()
                splash.destroy()
            if main_root:
                main_root.destroy()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
        # Clean up resources
        if splash:
            try:
                if progress:
                    progress.stop()
                splash.destroy()
            except:
                pass
        if main_root:
            try:
                main_root.destroy()
            except:
                pass
        sys.exit(0)

    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()

        # Clean up resources
        if splash:
            try:
                if progress:
                    progress.stop()
                splash.destroy()
            except:
                pass
        if main_root:
            try:
                main_root.destroy()
            except:
                pass
        
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

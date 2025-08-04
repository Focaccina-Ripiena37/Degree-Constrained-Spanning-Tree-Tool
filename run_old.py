# run.py - Avvio semplice e pulito dell'app GUI

from app.gui import App
from app.splash_screen import show_splash_screen
import tkinter as tk
from tkinter import ttk
import os
import sys
import platform
import multiprocessing
import time

# Safe and adaptive CPU optimization to prevent system crashes
def configure_cpu_optimization(safety_margin=0.75):
    """
    Configure environment variables for safe CPU utilization with adaptive resource management.
    Uses only a fraction of available cores and monitors system resources to prevent crashes.

    Args:
        safety_margin (float): Safety margin for resource usage (0.0-1.0)

    Returns:
        int: Number of cores configured for use
    """
    try:
        # Import psutil for system monitoring
        try:
            import psutil
        except ImportError:
            print("⚠️ psutil not available. Using conservative CPU settings.")
            # Fallback to very conservative settings
            safe_cores = max(1, multiprocessing.cpu_count() // 2)
            os.environ["OMP_NUM_THREADS"] = str(safe_cores)
            os.environ["MKL_NUM_THREADS"] = str(safe_cores)
            os.environ["NUMEXPR_NUM_THREADS"] = str(safe_cores)
            os.environ["OPENBLAS_NUM_THREADS"] = str(safe_cores)
            print(f"✅ Conservative CPU configuration: {safe_cores} cores (fallback mode)")
            return safe_cores

        cpu_count = multiprocessing.cpu_count()

        # Monitor current system load and available memory
        try:
            cpu_load = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            available_ram_gb = memory.available / (1024**3)
        except Exception:
            # Fallback if monitoring fails
            cpu_load = 50.0
            available_ram_gb = 2.0

        # Calculate safe number of cores based on system state
        safe_cores = max(1, int(cpu_count * safety_margin))

        # Apply additional safety checks
        if available_ram_gb < 2.0:
            safe_cores = 1
            print("⚠️ Low memory detected: limiting to single-core operation")
        elif cpu_load > 90.0:
            safe_cores = max(1, safe_cores // 2)
            print(f"⚠️ High CPU load detected ({cpu_load:.1f}%): reducing core usage")
        elif available_ram_gb < 4.0:
            safe_cores = max(1, min(safe_cores, 2))
            print("⚠️ Limited memory: restricting to maximum 2 cores")

        # Set environment variables for scientific libraries with safe limits
        os.environ["OMP_NUM_THREADS"] = str(safe_cores)
        os.environ["MKL_NUM_THREADS"] = str(safe_cores)
        os.environ["NUMEXPR_NUM_THREADS"] = str(safe_cores)
        os.environ["OPENBLAS_NUM_THREADS"] = str(safe_cores)

        # Additional safety settings to prevent library conflicts
        os.environ["NUMBA_NUM_THREADS"] = str(safe_cores)
        os.environ["VECLIB_MAXIMUM_THREADS"] = str(safe_cores)

        # Configure NumPy if available
        try:
            import numpy as np
            print(f"✅ Safe CPU optimization configured: {safe_cores}/{cpu_count} cores")
            print(f"   System status: {cpu_load:.1f}% CPU load, {available_ram_gb:.1f}GB available RAM")
        except ImportError:
            print(f"✅ Safe CPU optimization configured: {safe_cores}/{cpu_count} cores (NumPy not available)")

        return safe_cores

    except Exception as e:
        print(f"❌ Error in CPU configuration: {e}")
        # Emergency fallback to single core
        safe_cores = 1
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["MKL_NUM_THREADS"] = "1"
        os.environ["NUMEXPR_NUM_THREADS"] = "1"
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
        print(f"🛑 Emergency fallback: using single core due to configuration error")
        return safe_cores

def set_application_icon(root):
    """
    Set the application icon for the main window.
    Handles cross-platform icon setting with fallbacks.
    """
    icon_paths = [
        "icon.ico",
        os.path.join(os.path.dirname(__file__), "icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "app", "icon.ico")
    ]

    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            try:
                if platform.system() == "Windows":
                    root.iconbitmap(default=icon_path)
                    return True
                else:
                    # For macOS and Linux
                    try:
                        from PIL import Image, ImageTk
                        img = Image.open(icon_path)
                        img = img.resize((32, 32), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        # Store reference to prevent garbage collection
                        root._icon_photo = photo
                        root.iconphoto(True, photo)
                        return True
                    except ImportError:
                        # Fallback if PIL is not available
                        try:
                            root.iconbitmap(default=icon_path)
                            return True
                        except:
                            continue
                    except Exception as e:
                        print(f"Icon loading error: {e}")
                        continue
            except Exception as e:
                print(f"Icon path error: {e}")
                continue

    return False

def initialize_application():
    """
    Initialize the main application with proper startup sequence.

    Returns:
        tuple: (root, app, title_suffix) or (None, None, None) on failure
    """
    try:
        # Configure CPU optimization
        print("⚙️ Configuring system resources...")
        cpu_count = configure_cpu_optimization()

        # Import adaptive scaling functions
        print("🔍 Detecting system capabilities...")
        try:
            from app.algorithms import detect_system_resources, classify_system_type, check_user_overrides

            # Detect and classify system
            cpu_cores, total_ram_gb, available_ram_gb = detect_system_resources()
            system_type, safety_margin, ram_efficiency = classify_system_type(cpu_cores, available_ram_gb)
            user_overrides = check_user_overrides()

            # Show system classification
            print(f"🖥️ System Classification: {system_type.upper()}")
            print(f"📊 Hardware: {cpu_cores} cores, {total_ram_gb:.1f}GB total RAM, {available_ram_gb:.1f}GB available")
            print(f"⚙️ Adaptive Settings: {safety_margin:.0%} safety margin, {ram_efficiency:.0%} RAM efficiency")

            if user_overrides['force_conservative']:
                print("🛡️ CONSERVATIVE MODE: Forced via environment variable")
                title_suffix = "CONSERVATIVE MODE"
            elif system_type == "workstation":
                print("🚀 WORKSTATION MODE: Maximum performance scaling enabled")
                title_suffix = f"WORKSTATION MODE ({cpu_cores} cores)"
            elif system_type == "desktop":
                print("🖥️ DESKTOP MODE: Moderate performance scaling")
                title_suffix = f"DESKTOP MODE ({cpu_cores} cores)"
            else:
                print("💻 LAPTOP MODE: Conservative resource usage")
                title_suffix = f"LAPTOP MODE ({cpu_cores} cores)"

            if user_overrides['max_workers']:
                print(f"👤 User Override: Max workers limited to {user_overrides['max_workers']}")
            if user_overrides['safety_margin']:
                print(f"👤 User Override: Safety margin set to {user_overrides['safety_margin']:.0%}")

        except Exception as e:
            print(f"⚠️ Could not detect system classification: {e}")
            title_suffix = f"SAFE MODE ({cpu_count} cores)"

        # Initialize main application window
        print("🖥️ Initializing GUI components...")
        root = tk.Tk()
        root.title(f"DCST Tool - {title_suffix}")

        # Hide main window initially
        root.withdraw()

        # Set application icon
        print("🎨 Loading application resources...")
        icon_set = set_application_icon(root)
        if icon_set:
            print("✅ Application icon loaded successfully")
        else:
            print("⚠️ Could not load application icon")

        # Create progress bar and app
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")

        print("🔧 Finalizing setup...")
        app = App(root, progress_bar)

        print("🚀 Starting DCST Tool with Adaptive Scaling...")
        print("📖 See ADAPTIVE_SCALING_GUIDE.md for configuration options")

        # Show screen detection info
        try:
            from app.utils import get_screen_info
            screen_info = get_screen_info()
            print(f"🖥️ Display: {screen_info['screen_width']}x{screen_info['screen_height']} "
                  f"({screen_info['scale_factor']}) - Window: {screen_info['optimal_width']}x{screen_info['optimal_height']}")
        except Exception as e:
            print(f"⚠️ Screen detection info unavailable: {e}")

        return root, app, title_suffix

    except Exception as e:
        print(f"❌ Failed to initialize application: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

if __name__ == "__main__":
    try:
        print("🚀 Starting DCST Tool...")

        # Create main root window first
        root = tk.Tk()
        root.withdraw()  # Hide initially

        # Show splash screen with manual control
        splash = show_splash_screen(parent_root=root, duration=3.0, manual_mode=True)

        if splash:
            # Update splash screen during initialization
            splash.update_status("Configuring system resources...", 20)

            # Initialize application components
            main_root, app, title_suffix = initialize_application()

            if main_root and app:
                splash.update_status("Loading application resources...", 80)

                # Update window title
                main_root.title(f"DCST Tool - {title_suffix}")

                splash.update_status("Ready!", 100)
                time.sleep(0.5)  # Brief pause to show "Ready!" message

                # Close splash screen
                splash.close()

                # Destroy the initial root and use the main root
                root.destroy()

                # Show main window
                print("✅ Launching main application window...")
                main_root.deiconify()
                main_root.lift()
                main_root.focus_force()

                # Start the main event loop
                main_root.mainloop()
            else:
                print("❌ Failed to initialize application")
                if splash:
                    splash.close()
                root.destroy()
                sys.exit(1)
        else:
            print("⚠️ Could not create splash screen, starting without it...")
            # Fallback: start without splash screen
            main_root, app, title_suffix = initialize_application()
            if main_root and app:
                root.destroy()  # Destroy the initial root
                main_root.deiconify()
                main_root.mainloop()
            else:
                print("❌ Failed to initialize application")
                root.destroy()
                sys.exit(1)

    except Exception as e:
        import traceback
        import datetime

        # Create detailed crash log
        crash_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_log_file = f"crash_log_{crash_time}.txt"

        try:
            with open(crash_log_file, "w", encoding="utf-8") as f:
                f.write(f"DCST Tool Crash Report - {datetime.datetime.now()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Error: {str(e)}\n\n")
                f.write("Full Traceback:\n")
                f.write("-" * 40 + "\n")
                traceback.print_exc(file=f)
                f.write("\n" + "-" * 40 + "\n")

                # Add system information
                try:
                    import psutil
                    f.write(f"\nSystem Information:\n")
                    f.write(f"CPU cores: {psutil.cpu_count()}\n")
                    f.write(f"CPU usage: {psutil.cpu_percent()}%\n")
                    memory = psutil.virtual_memory()
                    f.write(f"Total RAM: {memory.total / (1024**3):.1f} GB\n")
                    f.write(f"Available RAM: {memory.available / (1024**3):.1f} GB\n")
                    f.write(f"RAM usage: {memory.percent}%\n")
                except:
                    f.write("Could not retrieve system information\n")

            print(f"❌ CRITICAL ERROR: Application crashed!")
            print(f"📝 Crash log saved to: {crash_log_file}")
            print(f"🔍 Error: {str(e)}")

        except Exception as log_error:
            print(f"❌ CRITICAL ERROR: Application crashed and could not save log!")
            print(f"🔍 Original error: {str(e)}")
            print(f"🔍 Log error: {str(log_error)}")

        # Re-raise the exception to ensure proper exit code
        raise

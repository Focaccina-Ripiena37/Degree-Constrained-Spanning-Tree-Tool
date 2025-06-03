# run.py - Avvio semplice e pulito dell'app GUI

from app.gui import App
import tkinter as tk
from tkinter import ttk
import os
import multiprocessing

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

if __name__ == "__main__":
    try:
        # Configure CPU optimization before starting the application
        cpu_count = configure_cpu_optimization()

        # Import adaptive scaling functions to show system classification
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

        root = tk.Tk()
        root.title(f"DCST Tool - {title_suffix}")

        # Imposta icona se disponibile
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                try:
                    root.iconbitmap(default=icon_path)
                except:
                    pass  # Evita crash se l'icona non è compatibile
        except NameError:
            # Handle case when __file__ is not defined
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                try:
                    root.iconbitmap(default=icon_path)
                except:
                    pass

        # Crea barra di progresso e avvia l'app
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
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

        root.mainloop()

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

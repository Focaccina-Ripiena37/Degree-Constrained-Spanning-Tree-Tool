# Minimal GUI for DCST Tool
# - Simple parameters: n for three instances, degree constraint k, penalty, and p
# - Start/Stop controls
# - Determinate progress bar to show activity
# - Log area for status and results
# - No splash, themes, animations, or platform-specific styling

import threading
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
import time
import logging
import sys

# Core functions used (kept simple and direct)
from .algorithms import run_instance, evaluate_solution, StopRequested
from .utils import (
    generate_connected_random_graph,
    draw_and_save_graph,
    save_table_as_image,
    plot_score_evolution,
    get_current_plot_directory,
    reset_plot_directory,
    delete_current_plot_directory,
)
try:
    import pandas as pd
except Exception:
    pd = None

logging.getLogger(__name__).addHandler(logging.NullHandler())

class App:
    def __init__(self, root, progress_bar=None):
        self.root = root
        self.root.title("DCST Tool")
        self.root.geometry("600x750")
        # No application icon: keep the app minimal and academic-focused

        # State
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.results = {}

        # Variables (sane defaults)
        self.n_small = tk.IntVar(value=10)
        self.n_medium = tk.IntVar(value=50)
        self.n_large = tk.IntVar(value=200)
        self.max_children = tk.IntVar(value=3)
        self.penalty = tk.IntVar(value=1000)
        self.p_val = tk.DoubleVar(value=0.3)

        # Build UI
        self._build_ui(progress_bar)

        # Window close handling
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self, external_progress_bar):
        # Header with About button (top-right)
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(header, text="Parametri", font=(None, 10, "bold")).pack(side="left")
        about_btn = ttk.Button(header, text="Informazioni", command=lambda: webbrowser.open_new_tab("https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool"))
        about_btn.pack(side="right")

        # Two-column content area: left = normal parameters, right = Advanced Mode
        content = tk.Frame(self.root)
        content.pack(fill="x", padx=10, pady=6)

        left_col = tk.Frame(content)
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 10))

        right_col = tk.Frame(content)
        right_col.pack(side="left", fill="x", expand=True)

        # Parameters frame in left column (normal parameters on the left)
        params = tk.LabelFrame(left_col, text="Generali")
        params.pack(fill="x")

        # Simple grid for parameters
        def add_row(r, label, var, width=10):
            tk.Label(params, text=label).grid(row=r, column=0, padx=6, pady=4, sticky="w")
            tk.Entry(params, textvariable=var, width=width).grid(row=r, column=1, padx=6, pady=4, sticky="w")

        add_row(0, "Piccola:", self.n_small)
        add_row(1, "Media:", self.n_medium)
        add_row(2, "Grande:", self.n_large)
        add_row(3, "Grado massimo (k):", self.max_children)
        add_row(4, "Penalità:", self.penalty)
        add_row(5, "Prob. di connessione:", self.p_val)

        # Advanced Mode (right column)
        self.advanced_mode = tk.BooleanVar(value=False)
        adv_toggle = ttk.Checkbutton(right_col, text="Modalità Avanzata", variable=self.advanced_mode, command=self._toggle_advanced)
        adv_toggle.pack(anchor="w")

        # Advanced container with two labeled sections: Local Search and Simulated Annealing
        self.adv_container = tk.Frame(right_col)

        # Variables for advanced params
        self.ls_m = tk.IntVar(value=10)           # Local Search sample size
        self.ls_iters = tk.IntVar(value=500)      # Local Search iterations (max)
        self.sa_temp = tk.DoubleVar(value=100.0)  # SA temperature
        self.sa_cooling = tk.DoubleVar(value=0.95)  # SA cooling factor
        self.sa_iters = tk.IntVar(value=1000)     # SA iterations

        # Local Search frame
        self.ls_frame = tk.LabelFrame(self.adv_container, text="Local Search")
        self.ls_frame.columnconfigure(1, weight=1)

        # Simulated Annealing frame
        self.sa_frame = tk.LabelFrame(self.adv_container, text="Simulated Annealing")
        self.sa_frame.columnconfigure(1, weight=1)

        # Helper: clamp and set with optional rounding, preserving int/double Var types
        def _clamp_set(var, newv, vmin, vmax, ndigits=None):
            try:
                v = float(newv)
            except Exception:
                v = vmin
            v = max(vmin, min(vmax, v))
            if ndigits is not None:
                v = round(v, ndigits)
            if isinstance(var, tk.IntVar):
                var.set(int(v))
            else:
                var.set(v)

        # Sliders (Scale) for Advanced parameters
        # Local Search sample size m: 1..100 (int)
        tk.Label(self.ls_frame, text="Campione dell'intorno (m)").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        tk.Scale(self.ls_frame, from_=1, to=100, orient="horizontal", resolution=1, variable=self.ls_m, length=220).grid(row=0, column=1, sticky="we", padx=6, pady=(2, 8))
        m_btns = tk.Frame(self.ls_frame)
        m_btns.grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(2, 8))
        ttk.Button(m_btns, text="-", width=2, command=lambda: _clamp_set(self.ls_m, self.ls_m.get()-1, 1, 100)).pack(side="left", padx=2)
        ttk.Button(m_btns, text="+", width=2, command=lambda: _clamp_set(self.ls_m, self.ls_m.get()+1, 1, 100)).pack(side="left", padx=2)

        # Local Search iterations: 100..1000 (int)
        tk.Label(self.ls_frame, text="Iterazioni").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        tk.Scale(self.ls_frame, from_=100, to=1000, orient="horizontal", resolution=1, variable=self.ls_iters, length=220).grid(row=1, column=1, sticky="we", padx=6, pady=(2, 8))
        ls_iter_btns = tk.Frame(self.ls_frame)
        ls_iter_btns.grid(row=1, column=2, sticky="w", padx=(0, 6), pady=(2, 8))
        ttk.Button(ls_iter_btns, text="-", width=2, command=lambda: _clamp_set(self.ls_iters, self.ls_iters.get()-1, 100, 1000)).pack(side="left", padx=2)
        ttk.Button(ls_iter_btns, text="+", width=2, command=lambda: _clamp_set(self.ls_iters, self.ls_iters.get()+1, 100, 1000)).pack(side="left", padx=2)

        # Temperature: 1..1000 (int)
        tk.Label(self.sa_frame, text="Temperatura").grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        tk.Scale(self.sa_frame, from_=1, to=1000, orient="horizontal", resolution=1, variable=self.sa_temp, length=220).grid(row=0, column=1, sticky="we", padx=6, pady=(6, 2))
        temp_btns = tk.Frame(self.sa_frame)
        temp_btns.grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(6, 2))
        ttk.Button(temp_btns, text="-", width=2, command=lambda: _clamp_set(self.sa_temp, self.sa_temp.get()-1, 1, 1000)).pack(side="left", padx=2)
        ttk.Button(temp_btns, text="+", width=2, command=lambda: _clamp_set(self.sa_temp, self.sa_temp.get()+1, 1, 1000)).pack(side="left", padx=2)

        # Cooling rate: 0.80..0.999 (step 0.001)
        tk.Label(self.sa_frame, text="Fattore di raffreddamento").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        tk.Scale(self.sa_frame, from_=0.80, to=0.999, orient="horizontal", resolution=0.001, variable=self.sa_cooling, length=220).grid(row=1, column=1, sticky="we", padx=6, pady=2)
        cool_btns = tk.Frame(self.sa_frame)
        cool_btns.grid(row=1, column=2, sticky="w", padx=(0, 6), pady=2)
        ttk.Button(cool_btns, text="-", width=2, command=lambda: _clamp_set(self.sa_cooling, self.sa_cooling.get()-0.001, 0.80, 0.999, ndigits=3)).pack(side="left", padx=2)
        ttk.Button(cool_btns, text="+", width=2, command=lambda: _clamp_set(self.sa_cooling, self.sa_cooling.get()+0.001, 0.80, 0.999, ndigits=3)).pack(side="left", padx=2)

        # Iterations: 100..10000 (fine control to single unit)
        tk.Label(self.sa_frame, text="Iterazioni").grid(row=2, column=0, sticky="w", padx=6, pady=2)
        tk.Scale(self.sa_frame, from_=100, to=10000, orient="horizontal", resolution=1, variable=self.sa_iters, length=220).grid(row=2, column=1, sticky="we", padx=6, pady=(2, 8))
        iter_btns = tk.Frame(self.sa_frame)
        iter_btns.grid(row=2, column=2, sticky="w", padx=(0, 6), pady=(2, 8))
        ttk.Button(iter_btns, text="-", width=2, command=lambda: _clamp_set(self.sa_iters, self.sa_iters.get()-1, 100, 10000)).pack(side="left", padx=2)
        ttk.Button(iter_btns, text="+", width=2, command=lambda: _clamp_set(self.sa_iters, self.sa_iters.get()+1, 100, 10000)).pack(side="left", padx=2)

        # Pack sub-frames inside the container
        self.ls_frame.pack(fill="x", padx=8, pady=(4, 6))
        self.sa_frame.pack(fill="x", padx=8, pady=(0, 4))

        # Hidden by default, shown when checkbox is selected
        self.adv_container.pack_forget()

        # Controls frame
        controls = tk.Frame(self.root)
        controls.pack(fill="x", padx=10, pady=(0, 10))

        self.start_btn = ttk.Button(controls, text="Avvia", command=self.start_computation)
        self.stop_btn = ttk.Button(controls, text="Ferma", command=self.stop_computation, state="disabled")
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn.pack(side="left", padx=5)

        # Progress
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.progress = external_progress_bar or ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=2, pady=4)
        self.progress_label = tk.Label(progress_frame, text="Pronto")
        self.progress_label.pack(anchor="w", padx=2)

        # Log area
        log_frame = tk.LabelFrame(self.root, text="Registro")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=12)
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

        # Footer
        footer = tk.Frame(self.root)
        footer.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(footer, text="University of Ferrara - @2025 - MIT License").pack(side="left")
        # Disable until a Plot directory is created for this session
        self.open_plot_btn = ttk.Button(footer, text="Apri Cartella Plot", command=self.open_plot_dir, state="disabled")
        self.open_plot_btn.pack(side="right")

    def open_plot_dir(self):
        try:
            plot_dir = get_current_plot_directory()
            if not os.path.isdir(plot_dir):
                self.append_log("Cartella non trovata")
                return
            if os.name == 'nt':
                os.startfile(plot_dir)  # type: ignore[attr-defined]
            else:
                import subprocess
                # Try xdg-open (Linux) or open (macOS)
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', plot_dir])
                else:
                    subprocess.Popen(['xdg-open', plot_dir])
            self.append_log(f"Opened plot directory: {plot_dir}")
        except Exception as e:
            self.append_log(f"Could not open plot directory: {e}")

    def append_log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.update_idletasks()

    def set_progress(self, value, text=None, maximum=None):
        if maximum is not None:
            self.progress.configure(maximum=maximum)
        self.progress["value"] = value
        if text is not None:
            self.progress_label.config(text=text)
        self.progress.update_idletasks()

    def validate_inputs(self):
        try:
            nS, nM, nL = self.n_small.get(), self.n_medium.get(), self.n_large.get()
            k = self.max_children.get()
            pen = self.penalty.get()
            p = float(self.p_val.get())
            if any(n < 0 for n in (nS, nM, nL)):
                raise ValueError("n must be >= 0")
            if k <= 0:
                raise ValueError("k must be >= 1")
            if pen < 0:
                raise ValueError("penalty must be >= 0")
            if not (0.0 <= p <= 1.0):
                raise ValueError("p must be in [0, 1]")
            return True
        except Exception as e:
            messagebox.showerror("Invalid parameters", str(e))
            return False

    def start_computation(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        if not self.validate_inputs():
            return

        # Prepare run
        self.results = {}
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.append_log("Starting computation...")

        # Determine instances
        instances = []
        if self.n_small.get() > 0:
            instances.append(("Small", self.n_small.get()))
        if self.n_medium.get() > 0:
            instances.append(("Medium", self.n_medium.get()))
        if self.n_large.get() > 0:
            instances.append(("Large", self.n_large.get()))

        # Setup progress as determinate across instances
        self.set_progress(0, "Working...", maximum=max(1, len(instances)))

        # Ensure a fresh Plot directory per run (on Desktop or fallback)
        try:
            reset_plot_directory()
            plot_dir = get_current_plot_directory()
            self.append_log(f"Plot directory: {plot_dir}")
            # Enable the button once the directory is available
            try:
                if os.path.isdir(plot_dir):
                    self.open_plot_btn.configure(state="normal")
            except Exception:
                pass
        except Exception as e:
            self.append_log(f"Warning: could not create Plot directory: {e}")
            try:
                self.open_plot_btn.configure(state="disabled")
            except Exception:
                pass

        # Run in background
        self.worker_thread = threading.Thread(target=self._run_all, args=(instances,), daemon=True)
        self.worker_thread.start()

    def stop_computation(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set()
            self.append_log("Stop requested...")
        # Immediate UI reset and cleanup
        try:
            self.stop_btn.config(state="disabled")
            self.start_btn.config(state="normal")
            self.set_progress(0, "Pronto", maximum=1)
            self.open_plot_btn.configure(state="disabled")
        except Exception:
            pass
        try:
            delete_current_plot_directory()
        except Exception:
            pass
        # Let the background thread wind down on its own after noticing stop_event

    def _run_all(self, instances):
        k = self.max_children.get()
        pen = self.penalty.get()
        p = float(self.p_val.get())
        # Advanced SA parameters (only when enabled)
        use_adv = bool(self.advanced_mode.get())
        sa_kwargs = {}
        if use_adv:
            try:
                sa_kwargs = {
                    "sa_initial_temperature": float(self.sa_temp.get()),
                    "sa_cooling_rate": float(self.sa_cooling.get()),
                    "sa_max_iterations": int(self.sa_iters.get()),
                }
            except Exception:
                sa_kwargs = {}

        completed = 0
        total = max(1, len(instances))
        combined_rows = []  # accumulate rows for a single summary across all instances

        try:
            for name, n in instances:
                if self.stop_event.is_set():
                    break

                self._ui(lambda: self.append_log(f"[{name}] Generating graph with n={n}, p={p}"))
                G = generate_connected_random_graph(n, p)

                if self.stop_event.is_set():
                    break

                self._ui(lambda: self.append_log(f"[{name}] Running algorithms (k={k}, penalty={pen})..."))

                # Run core algorithm suite (returns a dict of results)
                try:
                    # Pass advanced SA parameters only if enabled
                    ls_m_val = int(self.ls_m.get()) if use_adv else 10
                    ls_iter_val = int(self.ls_iters.get()) if use_adv else 500
                    res = run_instance(
                        G=G,
                        max_children=k,
                        penalty=pen,
                        instance_name=name,
                        stop_event=self.stop_event,
                        root=0,
                        ls_sample_m=ls_m_val,
                        ls_max_iterations=ls_iter_val,
                        **sa_kwargs,
                    )
                except StopRequested:
                    # User-initiated stop: no popups, break fast
                    res = None
                    self._ui(lambda: self.append_log(f"[{name}] Interrotto dall'utente"))
                    break
                except Exception as e:
                    res = None
                    # Log and show a popup explaining the error; Greedy should always find a solution
                    self._ui(lambda: self.append_log(f"[{name}] Error during computation: {e}"))
                    try:
                        messagebox.showerror(
                            "Errore durante il calcolo",
                            f"Si è verificato un errore in '{name}'.\n"
                            f"Dettagli: {e}\n\n"
                            "La Greedy con vincolo soft dovrebbe sempre trovare uno spanning tree. "
                            "Verifica i parametri e riprova.",
                        )
                    except Exception:
                        pass
                    # Mostra una sola finestra di errore per questa eccezione

                self.results[name] = res

                # Generate and save images for this instance
                try:
                    # Always save the original graph image
                    draw_and_save_graph(G, f"{name}_graph.png", max_children=k, is_spanning_tree=False)

                    if res and isinstance(res, dict):
                        # Save trees if available
                        if res.get("greedy_tree") is not None:
                            draw_and_save_graph(res["greedy_tree"], f"{name}_greedy_tree.png", max_children=k, is_spanning_tree=True)
                        if res.get("local_tree") is not None:
                            draw_and_save_graph(res["local_tree"], f"{name}_local_tree.png", max_children=k, is_spanning_tree=True)
                        if res.get("sa_tree") is not None:
                            draw_and_save_graph(res["sa_tree"], f"{name}_sa_tree.png", max_children=k, is_spanning_tree=True)

                        # Score evolution
                        histories = {}
                        if res.get("greedy_score_history"):
                            histories["Greedy"] = res["greedy_score_history"]
                        if res.get("local_score_history"):
                            histories["Local"] = res["local_score_history"]
                        if res.get("sa_score_history"):
                            histories["SA"] = res["sa_score_history"]
                        if histories:
                            # Build MAUT reference values (fixed thresholds, independent of other algos)
                            # cost_ref: greedy cost if available, else fallback to max cost among solutions or 1
                            try:
                                greedy_cost = res.get("greedy_cost")
                            except Exception:
                                greedy_cost = None
                            try:
                                all_costs = [res.get("greedy_cost"), res.get("local_cost"), res.get("sa_cost")]
                                max_cost_any = max([c for c in all_costs if c is not None]) if any(c is not None for c in all_costs) else 1.0
                            except Exception:
                                max_cost_any = 1.0
                            ref = {
                                "cost_ref": float(greedy_cost) if greedy_cost is not None else float(max_cost_any),
                                "time_ref": 0.1,
                                "memory_ref": 100.0,  # MB
                            }
                            plot_score_evolution(histories, reference_final_values=ref, filename=f"{name}_score_evolution.png")

                        # Summary table (only combined, no per-instance images)
                        try:
                            plot_dir = get_current_plot_directory()
                            rows = []
                            items = [
                                ("Greedy", res.get("greedy_cost"), res.get("greedy_time"), res.get("greedy_memory"), res.get("greedy_violations")),
                                ("Local", res.get("local_cost"), res.get("local_time"), res.get("local_memory"), res.get("local_violations")),
                                ("SA", res.get("sa_cost"), res.get("sa_time"), res.get("sa_memory"), res.get("sa_violations")),
                            ]
                            # Reference values for MAUT scoring in table
                            greedy_cost = res.get("greedy_cost")
                            ref_vals = {
                                "cost_ref": float(greedy_cost) if greedy_cost is not None else float(max([i[1] for i in items if i[1] is not None] or [1.0])),
                                "time_ref": 0.1,
                                "memory_ref": 100.0,  # MB
                            }

                            for algo_label, cost, tsec, mem, viol in items:
                                if cost is None:
                                    continue
                                sol = {
                                    "cost": float(cost),
                                    # Round time to 5 decimals for display stability
                                    "execution_time": float(round(float(tsec or 0.0), 5)),
                                    "memory": float(mem or 0.0),
                                    "violations": int(viol or 0),
                                }
                                try:
                                    score = evaluate_solution(sol, ref_vals)
                                except Exception:
                                    score = 0.0
                                rows.append({
                                    "Istanza": name,
                                    "Algoritmo": algo_label,
                                    "Costo": sol["cost"],
                                    "Tempo (s)": sol["execution_time"],
                                    # Show N/A when memory not measured (0 or None)
                                    "Memoria (KB)": ("—" if (mem is None or float(mem or 0.0) == 0.0) else sol["memory"]),
                                    "Violazioni": sol["violations"],
                                    "Punteggio": score,
                                })

                            if rows and pd is not None:
                                df = pd.DataFrame(rows)
                                # Accumula le righe per generare una singola tabella riepilogativa combinata
                                combined_rows.extend(rows)
                        except Exception as e:
                            self._ui(lambda: self.append_log(f"[{name}] Warning: could not save summary images: {e}"))
                except Exception as e:
                    self._ui(lambda: self.append_log(f"[{name}] Warning: image generation failed: {e}"))

                # Log a short summary
                if res and isinstance(res, dict):
                    self._ui(lambda: self.append_log(f"[{name}] Results captured"))
                    # Try to log costs if present
                    for alg_name, alg_result in res.items():
                        try:
                            if isinstance(alg_result, dict) and "cost" in alg_result:
                                cost = alg_result["cost"]
                                self._ui(lambda c=cost, a=alg_name: self.append_log(f"  - {a}: cost={c}"))
                        except Exception:
                            pass
                else:
                    self._ui(lambda: self.append_log(f"[{name}] No results"))

                completed += 1
                self._ui(lambda: self.set_progress(completed, f"Progress: {completed}/{total}"))

            # After all instances: save combined summary image
            try:
                if combined_rows and pd is not None:
                    plot_dir = get_current_plot_directory()
                    combined_df = pd.DataFrame(combined_rows)
                    save_table_as_image(combined_df, os.path.join(plot_dir, "summary.png"))
            except Exception as e:
                self._ui(lambda: self.append_log(f"[Summary] Warning: could not save combined summary: {e}"))

            if self.stop_event.is_set():
                self._ui(lambda: self.append_log("Computation stopped by user"))
            else:
                self._ui(lambda: self.append_log("All computations completed"))

        finally:
            # Reset UI
            self._ui(lambda: self._reset_controls())

    def _reset_controls(self):
        self.stop_btn.config(state="disabled")
        self.start_btn.config(state="normal")
        self.set_progress(0, "Pronto", maximum=1)
        try:
            self.open_plot_btn.configure(state="disabled")
        except Exception:
            pass

    def _ui(self, fn):
        # Thread-safe UI updates
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def _on_close(self):
        self.stop_computation()
        # Give the thread a moment to notice stop_event
        for _ in range(20):
            if not (self.worker_thread and self.worker_thread.is_alive()):
                break
            time.sleep(0.05)
        self.root.destroy()

    def _toggle_advanced(self):
        try:
            if self.advanced_mode.get():
                # Show the advanced container and ensure its children are packed
                self.adv_container.pack(fill="x", padx=12, pady=(0, 8))
            else:
                self.adv_container.pack_forget()
        except Exception:
            pass

def lazy_load_algorithms():
    """Lazy load only the minimal set of functions actually used by the GUI."""
    from .algorithms import test_instance, evaluate_solution
    from .utils import (
        generate_connected_random_graph,
        draw_and_save_graph,
        save_table_as_image,
        reset_plot_directory,
        get_current_plot_directory,
    )
    return (
        test_instance,
        evaluate_solution,
        generate_connected_random_graph,
        draw_and_save_graph,
        save_table_as_image,
        reset_plot_directory,
        get_current_plot_directory,
    )
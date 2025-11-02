# 🌳 DCST Tool – Degree-Constrained Spanning Tree Solver

> Note (2025-11): This repository now targets a simplified academic profile focused on clarity and teaching.
> It includes a minimal Tkinter GUI and three algorithms (Greedy, Local Search, Simulated Annealing).
> Advanced systems (performance tracking, adaptive parallelization, heavy packaging, splash/theme polish) were removed or deprecated.
> Results (graphs, trees, tables, score plots) are saved as images under your Desktop/Plot/ directory.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](BUILD_INSTRUCTIONS.md)
[![Last Commit](https://img.shields.io/github/last-commit/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.svg)](../../commits/main)
[![Open Issues](https://img.shields.io/github/issues/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.svg)](../../issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.svg)](../../pulls)
[![Contributors](https://img.shields.io/github/contributors/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.svg)](../../graphs/contributors)
[![Code Style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)
[![Tests](https://img.shields.io/badge/tests-6%20passing-brightgreen.svg)](../../actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](../../blob/main/CONTRIBUTING.md)

**DCST Tool** is a compact, student-friendly graphical application developed in Python for the **Degree-Constrained Minimum Spanning Tree (DCMST)** problem. In this simplified academic profile the focus is on clarity, consistency, and results visualization.

## Dependencies (minimal)

- Required: `networkx`, `matplotlib`
- Optional: `pandas` (only for saving the combined summary table image; the app runs fine without it)

Install with:

```
pip install -r requirements.txt
```

## 📋 Problem Statement

Given a weighted, non-complete graph and a root node r, find the minimum cost spanning tree rooted at r such that each node has at most k children (degree constraint).

```
INPUT:  Weighted graph G = (V, E), root node r, degree constraint k
OUTPUT: Minimum cost spanning tree T with degree constraints satisfied
```

## 🎯 Algorithmic Approaches

The tool implements and compares three different algorithmic strategies for solving the DCMST problem:

### 🔧 **Greedy (Kruskal MST + penalty)**
- **Type**: Constructive algorithm
- **Approach**: Kruskal MST ignoring degree limits during construction; degree violations are penalized in the cost function (no hard enforcement during build)
- **Implementation**: Sort edges by weight, Union-Find for cycle detection; final cost = sum(weights) + penalty · excess_degree
- **Characteristics**: Very fast, provides a strong baseline for subsequent improvement
- **Time Complexity**: O(E log E)

### 🔄 **Hill Climbing (First Improvement Local Search)**
- **Type**: Local search metaheuristic
- **Approach**: Edge-swap operations with first improvement strategy
- **Implementation**: Remove edge → find reconnecting edge → accept first improvement
- **Characteristics**: Improves greedy solutions, reaches local optima
- **Termination**: When no improving neighbor is found

### 🔥 **Simulated Annealing**
- **Type**: Probabilistic metaheuristic
- **Approach**: Temperature-based acceptance with edge-swap operators
- **Implementation**: Accept improvements always, accept worse solutions with probability exp(-Δ/T)
- **Characteristics**: Escapes local optima, explores solution space extensively
- **Cooling Schedule**: Exponential temperature reduction (T = T × α)

## ✨ Features

### 🖥️ **GUI (Simplified)**
- Basic Tkinter interface with normal parameters (left) and an optional Advanced Mode (right) for SA parameters
- Determinate progress bar and a small log panel
- Outputs saved to Desktop/Plot/ (auto-created); a dedicated “Apri Cartella Plot” button opens the folder

### 📊 **Analysis & Visualization**
- Graph and spanning tree visualization (NetworkX + Matplotlib)
- Comparison table image and raw score-evolution plot image
- Basic metrics: cost, runtime, and degree-constraint violations

### 🚀 Packaging
- Executable packaging is currently out-of-scope for the simplified profile.

## 📦 Installation & Usage

### 🎯 **For End Users**
Binary packaging is currently out-of-scope for the simplified profile. Please use the developer setup below. On Windows, you can also run `install_dependencies.cmd` to create a virtual environment and install requirements automatically (add `--with-pandas` to enable the optional summary table image).

### 🛠️ **For Developers**

#### Prerequisites
- Python 3.10 or later
- pip package manager
- Git (for cloning)

#### Installation Steps
```
# Clone
git clone https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git
cd Degree-Constrained-Spanning-Tree-Tool

# Create and activate a virtual environment (recommended)
python -m venv .venv
\.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install minimal dependencies
pip install -r requirements.txt

# (Optional) Install extras for table image rendering
# pip install pandas

# Run tests (optional)
python -m pytest -q

# Run the application
python run.py
```

#### Platform-Specific Setup

**Windows:**
```cmd
# Quick start (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; python run.py

# In alternativa, script guidato (crea .venv e installa deps):
./install_dependencies.cmd
```

**macOS:**
```bash
# Create and activate venv, then install and run
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python run.py
```

**Linux:**
```bash
# Install dependencies
pip3 install -r requirements.txt

# Launch the application
python3 run.py
```

## 🎮 Usage Instructions

### Basic Workflow
1. **Launch Application**: Start DCST Tool (no splash screen)
2. **Configure Parameters**:
   - Set graph sizes (Small: 10, Medium: 50, Large: 200 nodes)
   - Adjust degree constraint (k = maximum children per node)
   - Set penalty value for constraint violations
   - Configure connection probability multiplier
3. **Run Algorithms**: Click "Start" to execute all three algorithms
4. **Monitor Progress**: Watch real-time progress updates and status messages
5. **View Results**: Analyze generated graphs, spanning trees, and performance metrics
6. **Export Data**: Results automatically saved to `~/Desktop/Plot/`

### Advanced Configuration
- Advanced Mode: tune SA temperature, cooling rate, and iterations
- Stop functionality: interrupt long runs

### Output Files
Results are automatically saved to your Desktop in the `Plot/` directory:
- **Initial Graphs**: Visualization of generated test graphs
- **Optimized Trees**: Spanning trees found by each algorithm
- **Comparison Table**: Performance metrics and solution quality
- **Score Charts**: Algorithm performance over time
- **Detailed Logs**: Execution statistics and constraint violation reports

## 🔧 Building Executables
Out of scope for the current simplified profile. A future roadmap item.

## 📊 System Requirements

### Minimum Requirements
- **RAM**: 4 GB (8 GB recommended)
- **Storage**: 500 MB free space
- **CPU**: Any modern processor (multi-core recommended for large graphs)

### Platform Compatibility
- **Windows**: Windows 10/11 (64-bit) ✅
- **macOS**: macOS 10.14 (Mojave) or later ✅
- **Linux**: Most modern distributions (64-bit) ✅

### Performance Guidelines
- **Small Graphs** (< 50 nodes): All algorithms perform well on any system
- **Medium Graphs** (50-200 nodes): Good performance with default settings
- **Large Graphs** (200+ nodes): May require parameter tuning and more powerful hardware

## 🧪 Technology Stack

### Core Technologies
- **Python 3.10+**: Main programming language
- **Tkinter**: Cross-platform GUI framework
- **NetworkX**: Graph algorithms and data structures
- **Matplotlib**: Graph visualization and plotting
- **(Optional) Pandas**: Combined summary table image export

### Additional Libraries
- **PIL/Pillow**: Image processing (via Matplotlib)

### Build Tools
- (Deferred in simplified profile)

## 📚 Documentation
Older build/distribution documents may refer to advanced features that are no longer present.

### Algorithm Documentation
Each algorithm implementation follows standardized approaches:
- **Greedy**: Modified Kruskal with Union-Find and degree constraints
- **Hill Climbing**: First improvement with edge-swap neighborhood
- **Simulated Annealing**: Exponential cooling with probabilistic acceptance

### Punteggio (MAUT, utilità esponenziale, log su tempo/memoria)

Per confrontare soluzioni con attributi eterogenei (costo, tempo, memoria) il tool utilizza una funzione di punteggio accademica basata sulla Multi-Attribute Utility Theory (MAUT) con:

- combinazione additiva pesata delle componenti (costo, tempo, memoria);
- trasformazione logaritmica su tempo e memoria (rendimenti decrescenti su scale fortemente asimmetriche);
- utility esponenziale negativa per comprimere code alte e garantire output in [0,100].

Riferimenti essenziali: Keeney & Raiffa (1976), “Decisions with Multiple Objectives: Preferences and Value Tradeoffs”.

Formula (sintesi):

- Costo effettivo: C_eff = cost + λ · violations
- Perdita aggregata: L = w_cost · (C_eff / cost_ref) + w_time · ln(1 + time_s / time_ref) + w_mem · ln(1 + memory_mb / memory_ref)
- Punteggio (mapping): score = 100 · exp(-L)  (oppure 100/(1+L))

Valori di riferimento (indipendenti dal confronto tra algoritmi):

- cost_ref: costo atteso/baseline (nel tool: costo Greedy dell’istanza, se disponibile)
- time_ref: 0.1 s (tempo “accettabile”)
- memory_ref: 100 MB (memoria “accettabile”)

Pesi (importanza relativa): w_cost = 0.7, w_time = 0.2, w_mem = 0.1 (costo > tempo > memoria).

Snippet (semplificato):

```python
from math import log, exp

def compute_score(cost, violations, time_s, memory_mb, cost_ref, time_ref=0.1, memory_ref=100.0,
              w_cost=0.7, w_time=0.2, w_mem=0.1, lambda_penalty=10.0, mapping="exp"):
   # Rinormalizza i pesi se la memoria non è disponibile
   if memory_mb is None:
      total = w_cost + w_time
      w_cost, w_time, w_mem = w_cost/total, w_time/total, 0.0

   cost_eff = cost + lambda_penalty * float(violations)
   L = w_cost * (cost_eff / cost_ref) + w_time * log(1 + time_s / time_ref)
   if memory_mb is not None:
      L += w_mem * log(1 + memory_mb / memory_ref)

   return 100.0 * exp(-L) if mapping == "exp" else 100.0 / (1.0 + L)
```

Nel codice del tool, la funzione `evaluate_solution` è un wrapper che prepara i dati (notare che la memoria misurata internamente è in KB e viene convertita in MB per lo scoring) e invoca `compute_score` con i riferimenti sopra. Lo stesso schema è usato nei grafici “score evolution”, così tabella e grafico sono coerenti.

#### 📦 Riquadro teoria e riferimenti (scoring)

> Perché MAUT e perché così?
>
> - Multi-Attribute Utility Theory (MAUT) consente di aggregare attributi eterogenei (costo, tempo, memoria) in modo coerente con preferenze e trade-off; l’additività è appropriata se gli attributi sono indipendenti in utilità (Keeney & Raiffa, 1976).
> - La mappatura esponenziale negativa, score = 100·exp(−L), garantisce monotonia e comprime code alte (robusta a outlier su tempo/memoria); l’alternativa 100/(1+L) è più lineare ma meno “outlier-robust”.
> - I log su tempo/memoria modellano rendimenti decrescenti su scale molto asimmetriche (passare da 0.05→0.1 s “pesa” più che da 5→5.05 s).
> - I pesi (0.7, 0.2, 0.1) riflettono una priorità didattica: costo ≫ tempo > memoria. Sono normalizzati automaticamente se la memoria non è disponibile.
> - Penalità di violazione (λ ≈ 10.0) converte “violazioni” in unità di costo; 1 violazione vale circa 10 unità di costo nel baseline. Aumentare λ enfatizza il rispetto dei vincoli.
>
> Proprietà utili
>
> - Monotonicità: aumentando cost/violations/time/memory, L cresce e lo score decresce.
> - Bordi: L→0 implica score→100; L grande implica score→0 ma mai negativo.
> - Coerenza tra vista tabellare e grafico: entrambi invocano la stessa formula e gli stessi riferimenti.
>
> Sensibilità/come tarare
>
> - cost_ref: usare il Greedy della stessa istanza stabilizza i confronti; in alternativa, un costo noto/atteso.
> - time_ref/memory_ref: scegliere soglie “accettabili” (0.1 s; 100 MB) secondo il contesto hardware/didattico.
> - w_cost/w_time/w_mem: calibrare in base alle priorità del corso/tesi; mantenere somma=1.
>
> Riferimenti
>
> - Keeney, R.L., Raiffa, H. (1976). Decisions with Multiple Objectives: Preferences and Value Tradeoffs. Wiley.
> - Fishburn, P.C. (1970). Utility Theory for Decision Making. Wiley.

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit with clear messages: `git commit -m "Add feature description"`
5. Push to your fork: `git push origin feature-name`
6. Create a Pull Request

### Contribution Guidelines
- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure cross-platform compatibility
- Test on multiple operating systems when possible

### Areas for Contribution
- Algorithm optimizations and new implementations
- GUI enhancements and usability improvements
- Performance optimizations for large graphs
- Additional export formats and visualization options
- Documentation improvements and translations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Developed for Operations Research coursework (A.A. 2024/2025)
- Simplified in 2025-11 for a student-friendly academic profile

## 📬 Support & Contact

- **Issues**: Report bugs or request features via [GitHub Issues](../../issues)
- **Discussions**: Join conversations in [GitHub Discussions](../../discussions)
- **Documentation**: Comprehensive guides available in the repository

---

🚀 **Ready to solve degree-constrained spanning tree problems?** Download the latest release or clone the repository to get started!

## 🗺️ Roadmap (lightweight)

- Improve figure DPI and layout consistency in saved images
- Optional dark theme for the Tkinter GUI
- Packaging (PyInstaller) for Windows/macOS/Linux with a tiny launcher

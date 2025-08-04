# 🌳 DCST Tool – Degree-Constrained Spanning Tree Solver

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](BUILD_INSTRUCTIONS.md)

**DCST Tool** is a comprehensive graphical application developed in Python for solving the **Degree-Constrained Minimum Spanning Tree (DCMST)** problem, a well-known NP-Hard optimization problem in Operations Research. The application is designed for educational and research purposes, with emphasis on **modularity**, **usability**, and **result visualization**.

## 📋 Problem Statement

Given a weighted, non-complete graph and a root node r, find the minimum cost spanning tree rooted at r such that each node has at most k children (degree constraint).

```
INPUT:  Weighted graph G = (V, E), root node r, degree constraint k
OUTPUT: Minimum cost spanning tree T with degree constraints satisfied
```

## 🎯 Algorithmic Approaches

The tool implements and compares three different algorithmic strategies for solving the DCMST problem:

### 🔧 **Modified Kruskal's Algorithm (Greedy)**
- **Type**: Constructive algorithm
- **Approach**: Union-Find based edge selection with degree constraints
- **Implementation**: Sort edges by weight, use Union-Find for cycle detection, maintain degree arrays
- **Characteristics**: Fast execution, provides good initial solutions
- **Time Complexity**: O(E log E + V α(V))

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

### 🖥️ **Cross-Platform GUI**
- **Native Appearance**: Platform-specific styling (light theme on macOS, dark on Windows/Linux)
- **Responsive Design**: Adaptive window sizing based on screen resolution
- **Real-time Progress**: Live algorithm progress tracking with detailed status updates
- **Professional Startup**: Branded splash screen with loading animation

### 📊 **Comprehensive Analysis**
- **Algorithm Comparison**: Side-by-side performance analysis
- **Visualization**: Graph and spanning tree visualization with NetworkX and Matplotlib
- **Export Capabilities**: Results saved as images, CSV files, and detailed reports
- **Performance Metrics**: Execution time, memory usage, constraint violations

### 🚀 **Portable Executables**
- **Windows**: Standalone .exe file (no Python installation required)
- **macOS**: Native .app bundle with proper icon and system integration
- **Self-contained**: All dependencies bundled, truly portable

## 📦 Installation & Usage

### 🎯 **For End Users (Recommended)**

#### Windows 10/11
1. Download `DCST_Tool_Windows.exe` from the [releases page](../../releases)
2. Double-click to run (may show security warning - click "Run anyway")
3. No installation or additional software required

#### macOS 10.14+
1. Download `DCST_Tool.app` from the [releases page](../../releases)
2. Drag to Applications folder (optional)
3. Right-click and select "Open" on first run (security requirement)
4. Subsequent runs: double-click to launch

### 🛠️ **For Developers**

#### Prerequisites
- Python 3.8 or later
- pip package manager
- Git (for cloning)

#### Installation Steps
```bash
# Clone the repository
git clone https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git
cd Degree-Constrained-Spanning-Tree-Tool

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

#### Platform-Specific Setup

**Windows:**
```cmd
# Run the automated setup
install_dependencies.cmd

# Launch the application
python run.py
# or double-click play.vbs
```

**macOS:**
```bash
# Give execution permissions and run setup
chmod +x setup_dcst.command
./setup_dcst.command

# Launch the application
python3 run.py
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
1. **Launch Application**: Start DCST Tool (splash screen will appear)
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
- **Advanced Mode**: Enable for fine-grained control over connection probabilities
- **Configuration Management**: Export/import settings for reproducible experiments
- **Stop Functionality**: Interrupt long-running computations safely

### Output Files
Results are automatically saved to your desktop in the `Plot/` directory:
- **Initial Graphs**: Visualization of generated test graphs
- **Optimized Trees**: Spanning trees found by each algorithm
- **Comparison Table**: Performance metrics and solution quality
- **Score Charts**: Algorithm performance over time
- **Detailed Logs**: Execution statistics and constraint violation reports

## 🔧 Building Executables

### Automated Build Process

**All Platforms:**
```bash
# Install build dependencies
python -m pip install pyinstaller>=6.0.0

# Run the build script
python build_executables.py
```

**Platform-Specific Scripts:**
```bash
# macOS/Linux
./build.sh

# Windows
build.bat
```

### Build Output
- **macOS**: `dist/DCST_Tool.app` (~244 MB)
- **Windows**: `dist/DCST_Tool_Windows.exe` (~200-250 MB)
- **Linux**: `dist/DCST_Tool_Linux` (~200-250 MB)

For detailed build instructions, see [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).

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
- **Python 3.8+**: Main programming language
- **Tkinter**: Cross-platform GUI framework
- **NetworkX**: Graph algorithms and data structures
- **Matplotlib**: Graph visualization and plotting
- **NumPy/SciPy**: Numerical computing and optimization
- **Pandas**: Data analysis and export functionality

### Additional Libraries
- **PIL/Pillow**: Image processing and manipulation
- **psutil**: System resource monitoring
- **tqdm**: Progress bar functionality
- **tabulate**: Table formatting and export

### Build Tools
- **PyInstaller**: Executable creation and packaging
- **setuptools/wheel**: Python packaging utilities

## 📚 Documentation

### Comprehensive Guides
- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)**: Complete build and distribution guide
- **[DISTRIBUTION_README.md](DISTRIBUTION_README.md)**: End-user installation and usage
- **[IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)**: Recent enhancements and features
- **[BUILD_SUMMARY.md](BUILD_SUMMARY.md)**: Build process results and verification

### Algorithm Documentation
Each algorithm implementation follows standardized approaches:
- **Greedy**: Modified Kruskal with Union-Find and degree constraints
- **Hill Climbing**: First improvement with edge-swap neighborhood
- **Simulated Annealing**: Exponential cooling with probabilistic acceptance

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
- Implements standardized algorithms from academic literature
- Built with modern Python best practices and cross-platform compatibility

## 📬 Support & Contact

- **Issues**: Report bugs or request features via [GitHub Issues](../../issues)
- **Discussions**: Join conversations in [GitHub Discussions](../../discussions)
- **Documentation**: Comprehensive guides available in the repository

---

🚀 **Ready to solve degree-constrained spanning tree problems?** Download the latest release or clone the repository to get started!

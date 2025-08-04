# DCST Tool - Portable Executable Distribution

## About

The Degree-Constrained Spanning Tree (DCST) Tool is a comprehensive application for solving degree-constrained minimum spanning tree problems using advanced algorithms including:

- **Greedy Algorithm**: Modified Kruskal's algorithm with Union-Find for efficient DCMST construction
- **Hill Climbing**: First improvement local search with edge swapping
- **Simulated Annealing**: Temperature-based optimization with adaptive cooling

## System Requirements

### macOS
- **Operating System**: macOS 10.14 (Mojave) or later
- **Architecture**: Intel x86_64 (compatible with Apple Silicon via Rosetta 2)
- **Memory**: 4 GB RAM recommended
- **Storage**: 500 MB free space

### Windows
- **Operating System**: Windows 10 or Windows 11
- **Architecture**: 64-bit (x64)
- **Memory**: 4 GB RAM recommended
- **Storage**: 500 MB free space
- **Additional**: No additional software required

### Linux
- **Operating System**: Most modern Linux distributions
- **Architecture**: x86_64
- **Memory**: 4 GB RAM recommended
- **Storage**: 500 MB free space

## Installation and Usage

### macOS

1. **Download**: Download the `DCST_Tool.app` bundle
2. **Extract**: If downloaded as a zip file, extract it
3. **Install**: Drag `DCST_Tool.app` to your Applications folder (optional)
4. **First Run**: Right-click the app and select "Open" (required for security)
5. **Subsequent Runs**: Double-click the app to launch

**Security Note**: macOS may show a security warning on first run. This is normal for unsigned applications. Click "Open" to proceed.

### Windows

1. **Download**: Download the `DCST_Tool_Windows.exe` file
2. **Run**: Double-click the executable to launch
3. **Security Warning**: Windows may show a security warning. Click "More info" then "Run anyway"

**Antivirus Note**: Some antivirus software may scan the executable. This is normal behavior for unsigned executables.

### Linux

1. **Download**: Download the `DCST_Tool_Linux` executable
2. **Set Permissions**: Open terminal and run: `chmod +x DCST_Tool_Linux`
3. **Run**: Execute with: `./DCST_Tool_Linux`

## Features

### Algorithm Implementations

- **Standardized Algorithms**: All algorithms follow textbook implementations
- **Union-Find Structure**: Efficient cycle detection with path compression
- **Edge-Swap Operators**: Common optimization operators across algorithms
- **Constraint Handling**: Proper degree constraint validation and violation counting

### User Interface

- **Intuitive GUI**: Easy-to-use graphical interface built with Tkinter
- **Graph Visualization**: Real-time visualization of graphs and spanning trees
- **Progress Tracking**: Live progress updates during algorithm execution
- **Result Export**: Save results in multiple formats (CSV, images, etc.)

### Performance Features

- **Adaptive Scaling**: Automatic resource management based on system capabilities
- **Multi-threading**: Parallel processing for improved performance
- **Memory Optimization**: Efficient memory usage for large graphs
- **Progress Reporting**: Real-time feedback on algorithm progress

## Usage Instructions

### Basic Workflow

1. **Launch Application**: Start the DCST Tool executable
2. **Load Graph**: Import your graph data (supported formats: various text formats)
3. **Configure Parameters**: Set degree constraints and algorithm parameters
4. **Run Algorithms**: Execute one or more algorithms on your graph
5. **View Results**: Analyze results through visualizations and statistics
6. **Export Data**: Save results for further analysis

### Graph Input Formats

The tool supports various graph input formats:
- Edge list format
- Adjacency matrix
- NetworkX compatible formats
- Custom text formats

### Algorithm Parameters

- **Max Children**: Maximum degree constraint for nodes
- **Penalty**: Penalty value for constraint violations
- **Iterations**: Maximum number of iterations for iterative algorithms
- **Temperature**: Initial temperature for simulated annealing
- **Cooling Rate**: Temperature reduction factor

## Performance Guidelines

### Recommended Graph Sizes

- **Small Graphs** (< 50 nodes): All algorithms perform well
- **Medium Graphs** (50-200 nodes): Good performance with default settings
- **Large Graphs** (200+ nodes): May require parameter tuning

### Memory Usage

- **Typical Usage**: 100-200 MB during normal operation
- **Large Graphs**: Memory usage scales with graph size
- **Peak Usage**: May temporarily increase during algorithm execution

### Processing Time

- **Greedy Algorithm**: Fast execution (seconds to minutes)
- **Hill Climbing**: Moderate execution time (minutes)
- **Simulated Annealing**: Longer execution time (minutes to hours for large graphs)

## Troubleshooting

### Common Issues

#### Application Won't Start

**macOS:**
- Ensure you right-clicked and selected "Open" on first run
- Check that your macOS version is 10.14 or later
- Try moving the app to Applications folder

**Windows:**
- Ensure you clicked "Run anyway" if Windows showed a security warning
- Check that you have Windows 10 or later
- Try running as administrator if needed

**Linux:**
- Ensure executable permissions are set: `chmod +x DCST_Tool_Linux`
- Check that you have required system libraries
- Try running from terminal to see error messages

#### Performance Issues

- **Slow Performance**: Reduce graph size or algorithm iterations
- **High Memory Usage**: Close other applications or use smaller graphs
- **Unresponsive Interface**: Allow algorithms to complete or use stop button

#### Algorithm Errors

- **Invalid Graph**: Ensure graph is connected and properly formatted
- **Constraint Violations**: Check degree constraint values
- **Parameter Errors**: Verify algorithm parameters are within valid ranges

### Getting Help

If you encounter issues:

1. **Check System Requirements**: Ensure your system meets minimum requirements
2. **Restart Application**: Close and reopen the application
3. **Check Input Data**: Verify graph data is properly formatted
4. **Reduce Complexity**: Try with smaller graphs or fewer iterations

## File Information

### Executable Details

#### macOS Version
- **File**: DCST_Tool.app
- **Size**: ~243 MB
- **Type**: macOS Application Bundle
- **Signature**: Unsigned (security warnings are normal)

#### Windows Version
- **File**: DCST_Tool_Windows.exe
- **Size**: ~200-250 MB (estimated)
- **Type**: Windows Executable
- **Signature**: Unsigned (security warnings are normal)

#### Linux Version
- **File**: DCST_Tool_Linux
- **Size**: ~200-250 MB (estimated)
- **Type**: Linux Executable
- **Permissions**: Requires execute permission

### What's Included

Each executable includes:
- Complete Python runtime environment
- All required libraries and dependencies
- Graph algorithms implementation
- GUI interface components
- Visualization tools
- Export functionality

### What's NOT Required

- Python installation
- Additional libraries or packages
- Internet connection (after download)
- Administrative privileges (for normal operation)

## Privacy and Security

- **No Network Access**: The application does not require internet connectivity
- **Local Processing**: All computations are performed locally on your machine
- **No Data Collection**: The application does not collect or transmit user data
- **File Access**: Only accesses files you explicitly open or save

## License and Credits

This tool implements standardized algorithms for degree-constrained spanning tree problems. The implementation follows established academic algorithms and best practices in computational optimization.

## Version Information

- **Version**: 1.0.0
- **Build Date**: August 2025
- **Compatibility**: Cross-platform (Windows, macOS, Linux)
- **Architecture**: 64-bit systems

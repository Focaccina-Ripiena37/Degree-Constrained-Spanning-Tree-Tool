# Contributing to DCST Tool

Thank you for your interest in contributing to the DCST Tool! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or later
- Git for version control
- Basic understanding of graph algorithms and optimization
- Familiarity with Python GUI development (Tkinter) for UI contributions

### Development Setup
1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/Degree-Constrained-Spanning-Tree-Tool.git
   cd Degree-Constrained-Spanning-Tree-Tool
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install pytest black flake8 mypy
   ```

3. **Verify Setup**
   ```bash
   # Run the application to ensure everything works
   python run.py
   ```

## 🔧 Development Guidelines

### Code Style
- Follow [PEP 8](https://pep8.org/) Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and modular
- Use type hints where appropriate

### Code Formatting
```bash
# Format code with black
black app/ run.py

# Check style with flake8
flake8 app/ run.py

# Type checking with mypy
mypy app/ run.py
```

### Project Structure
```
DCST-Tool/
├── app/                    # Main application package
│   ├── algorithms.py       # Algorithm implementations
│   ├── gui.py             # GUI components
│   ├── platform_styles.py # Platform-specific styling
│   ├── splash_screen.py   # Startup splash screen
│   └── utils.py           # Utility functions
├── build_executables.py   # Build script for executables
├── run.py                 # Main application entry point
├── requirements.txt       # Python dependencies
└── docs/                  # Documentation files
```

## 🎯 Areas for Contribution

### 1. Algorithm Improvements
- **Performance Optimization**: Improve algorithm efficiency for large graphs
- **New Algorithms**: Implement additional DCMST solving approaches
- **Parameter Tuning**: Enhance automatic parameter selection
- **Parallel Processing**: Add multi-threading support for algorithm execution

### 2. GUI Enhancements
- **User Experience**: Improve interface usability and workflow
- **Visualization**: Enhance graph and result visualization
- **Accessibility**: Add keyboard shortcuts and accessibility features
- **Themes**: Implement additional color themes and customization options

### 3. Platform Support
- **Linux Testing**: Improve Linux compatibility and testing
- **Mobile Support**: Explore mobile/tablet interface options
- **Web Interface**: Consider web-based version development
- **Performance**: Optimize for different hardware configurations

### 4. Documentation
- **Algorithm Documentation**: Detailed algorithm explanations
- **API Documentation**: Code documentation and examples
- **Tutorials**: Step-by-step usage guides
- **Translations**: Multi-language support

### 5. Testing and Quality
- **Unit Tests**: Expand test coverage for algorithms and utilities
- **Integration Tests**: GUI and workflow testing
- **Performance Tests**: Benchmarking and performance regression testing
- **Cross-Platform Testing**: Ensure compatibility across operating systems

## 📝 Contribution Process

### 1. Planning
- **Check Existing Issues**: Look for related issues or feature requests
- **Create Issue**: If none exists, create an issue describing your proposed changes
- **Discuss**: Engage with maintainers and community for feedback

### 2. Development
- **Create Branch**: Create a feature branch from main
  ```bash
  git checkout -b feature/your-feature-name
  ```
- **Make Changes**: Implement your changes following the guidelines
- **Test Thoroughly**: Ensure your changes work across platforms
- **Document**: Update documentation as needed

### 3. Testing
- **Run Existing Tests**: Ensure all existing functionality still works
- **Add New Tests**: Include tests for new functionality
- **Manual Testing**: Test the GUI and user workflows
- **Cross-Platform**: Test on multiple operating systems when possible

### 4. Submission
- **Commit Changes**: Use clear, descriptive commit messages
  ```bash
  git commit -m "Add feature: brief description of changes"
  ```
- **Push Branch**: Push your feature branch to your fork
  ```bash
  git push origin feature/your-feature-name
  ```
- **Create Pull Request**: Submit a PR with detailed description

## 🧪 Testing Guidelines

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_algorithms.py

# Run with coverage
python -m pytest --cov=app
```

### Test Structure
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **GUI Tests**: Test user interface functionality
- **Performance Tests**: Benchmark algorithm performance

### Writing Tests
- Use descriptive test names
- Test both success and failure cases
- Include edge cases and boundary conditions
- Mock external dependencies when appropriate

## 📚 Algorithm Implementation Guidelines

### Adding New Algorithms
1. **Research**: Ensure the algorithm is well-documented in literature
2. **Interface**: Follow the existing algorithm interface pattern
3. **Documentation**: Include algorithm description and complexity analysis
4. **Testing**: Provide comprehensive test cases
5. **Comparison**: Include performance comparison with existing algorithms

### Algorithm Interface
```python
def new_algorithm(G, max_children, penalty, **kwargs):
    """
    Brief description of the algorithm.
    
    Args:
        G: NetworkX graph
        max_children: Maximum degree constraint
        penalty: Penalty for constraint violations
        **kwargs: Additional algorithm-specific parameters
    
    Returns:
        tuple: (spanning_tree, total_cost)
    """
    # Implementation here
    pass
```

## 🐛 Bug Reports

### Before Reporting
- Check existing issues for duplicates
- Ensure you're using the latest version
- Test on a clean environment if possible

### Bug Report Template
```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Windows 10, macOS 12.0, Ubuntu 20.04]
- Python Version: [e.g., 3.9.7]
- DCST Tool Version: [e.g., 1.0.0]

**Additional Context**
Screenshots, logs, or other relevant information
```

## 💡 Feature Requests

### Feature Request Template
```markdown
**Feature Description**
Clear description of the proposed feature

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Implementation**
How should this feature work?

**Alternatives Considered**
Other approaches you've considered

**Additional Context**
Any other relevant information
```

## 📋 Code Review Process

### For Contributors
- Respond to feedback promptly
- Make requested changes in additional commits
- Keep discussions focused and professional
- Test changes thoroughly before requesting review

### Review Criteria
- **Functionality**: Does the code work as intended?
- **Style**: Does it follow project conventions?
- **Performance**: Are there any performance implications?
- **Documentation**: Is the code well-documented?
- **Testing**: Are there adequate tests?
- **Compatibility**: Does it work across platforms?

## 🏆 Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes for significant contributions
- GitHub contributor statistics
- Special recognition for major features or improvements

## 📞 Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Review**: For feedback on proposed changes
- **Documentation**: Check existing documentation first

## 📄 License

By contributing to DCST Tool, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to DCST Tool! Your efforts help make this tool better for everyone. 🚀

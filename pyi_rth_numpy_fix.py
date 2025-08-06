#!/usr/bin/env python3
"""
PyInstaller Runtime Hook for NumPy CPU Dispatcher Fix.

This runtime hook fixes the "CPU dispatcher tracer already initialized" error
that occurs when NumPy is imported multiple times in PyInstaller builds.

The hook ensures that NumPy's CPU dispatcher is only initialized once,
preventing conflicts that can cause the application to crash.
"""

import sys
import os

# Set environment variables to prevent NumPy CPU dispatcher conflicts
os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

# Prevent multiple NumPy initializations
_numpy_initialized = False

def _safe_numpy_import():
    """Safely import NumPy with CPU dispatcher protection."""
    global _numpy_initialized
    
    if _numpy_initialized:
        # NumPy already imported, return the existing module
        return sys.modules.get('numpy', None)
    
    try:
        # Set CPU dispatcher environment before first import
        os.environ['NPY_NUM_BUILD_JOBS'] = '1'
        
        # Import NumPy for the first time
        import numpy as np
        
        # Mark as initialized
        _numpy_initialized = True
        
        # Configure NumPy for PyInstaller compatibility
        if hasattr(np, 'seterr'):
            np.seterr(all='ignore')  # Suppress NumPy warnings
        
        return np
        
    except Exception as e:
        print(f"Warning: NumPy import failed: {e}")
        return None

# Pre-import NumPy to initialize CPU dispatcher safely
_safe_numpy_import()

# Monkey patch the import system to use our safe import
original_import = __builtins__.__import__

def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Patched import function that handles NumPy specially."""
    if name == 'numpy' or (isinstance(fromlist, (list, tuple)) and 'numpy' in str(fromlist)):
        # Use our safe NumPy import
        np_module = _safe_numpy_import()
        if np_module is not None:
            return np_module
    
    # For all other imports, use the original import function
    return original_import(name, globals, locals, fromlist, level)

# Apply the patch
__builtins__.__import__ = _patched_import

print("✅ NumPy CPU dispatcher fix applied")

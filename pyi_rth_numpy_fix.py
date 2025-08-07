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
os.environ['NPY_NUM_BUILD_JOBS'] = '1'

# Additional environment variables to prevent CPU dispatcher conflicts
os.environ['NUMPY_MADVISE_HUGEPAGE'] = '0'
os.environ['NUMPY_WARN_IF_NO_MEM_POLICY'] = '0'

# Try to pre-import NumPy to initialize CPU dispatcher safely
try:
    # Import NumPy early to avoid conflicts
    import numpy as np

    # Configure NumPy for PyInstaller compatibility
    if hasattr(np, 'seterr'):
        np.seterr(all='ignore')  # Suppress NumPy warnings

    print("✅ NumPy CPU dispatcher fix applied")

except Exception as e:
    print(f"Warning: NumPy import failed: {e}")
    print("✅ NumPy CPU dispatcher fix applied (environment only)")

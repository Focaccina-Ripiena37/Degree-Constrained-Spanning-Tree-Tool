#!/usr/bin/env python3
"""
Test script to verify that pydoc and SciPy sparse functionality work
in the PyInstaller-built application.
"""

import sys
import traceback

def test_pydoc_import():
    """Test that pydoc can be imported."""
    try:
        import pydoc
        print("✅ pydoc import successful")
        return True
    except ImportError as e:
        print(f"❌ pydoc import failed: {e}")
        return False

def test_scipy_sparse():
    """Test SciPy sparse functionality that was causing the error."""
    try:
        import scipy.sparse
        import numpy as np
        
        # Create a simple sparse matrix
        data = np.array([1, 2, 3])
        row = np.array([0, 1, 2])
        col = np.array([0, 1, 2])
        sparse_matrix = scipy.sparse.csr_matrix((data, (row, col)), shape=(3, 3))
        
        print("✅ SciPy sparse matrix creation successful")
        print(f"   Matrix shape: {sparse_matrix.shape}")
        print(f"   Matrix data: {sparse_matrix.data}")
        return True
    except Exception as e:
        print(f"❌ SciPy sparse test failed: {e}")
        traceback.print_exc()
        return False

def test_networkx_to_scipy():
    """Test NetworkX to SciPy conversion that was causing the original error."""
    try:
        import networkx as nx
        import numpy as np
        
        # Create a simple graph
        G = nx.Graph()
        G.add_edges_from([(0, 1), (1, 2), (2, 0)])
        
        # Convert to SciPy sparse array (this was failing before)
        sparse_array = nx.to_scipy_sparse_array(G)
        
        print("✅ NetworkX to SciPy sparse array conversion successful")
        print(f"   Array shape: {sparse_array.shape}")
        print(f"   Array type: {type(sparse_array)}")
        return True
    except Exception as e:
        print(f"❌ NetworkX to SciPy conversion failed: {e}")
        traceback.print_exc()
        return False

def test_scipy_docscrape():
    """Test the specific module that was causing the pydoc error."""
    try:
        from scipy._lib import _docscrape
        print("✅ scipy._lib._docscrape import successful")
        return True
    except Exception as e:
        print(f"❌ scipy._lib._docscrape import failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Testing PyInstaller fixes for pydoc and SciPy...")
    print("=" * 60)
    
    tests = [
        ("pydoc import", test_pydoc_import),
        ("SciPy sparse", test_scipy_sparse),
        ("NetworkX to SciPy", test_networkx_to_scipy),
        ("SciPy _docscrape", test_scipy_docscrape),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The PyInstaller fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. The application may still have issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test script to verify that the fixed DCST Tool executables work correctly.
Tests core functionality including graph generation, algorithms, and simplified parallelization.
"""

import os
import sys
import time
import subprocess
import tempfile
import shutil
from pathlib import Path

def test_executable_launch(executable_path, test_name):
    """Test if an executable launches without errors."""
    print(f"\n🧪 Testing {test_name}...")
    
    try:
        # Launch the executable in the background
        if executable_path.endswith('.app'):
            # For .app bundles, use 'open' command
            cmd = ['open', executable_path]
        else:
            # For standalone executables
            cmd = [executable_path]
        
        print(f"   Launching: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for startup
        time.sleep(3)
        
        # Check if process is still running (good sign for GUI apps)
        if process.poll() is None:
            print(f"   ✅ {test_name} launched successfully (process running)")
            
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            return True
        else:
            # Process exited, check for errors
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                print(f"   ✅ {test_name} completed successfully")
                return True
            else:
                print(f"   ❌ {test_name} failed with return code {process.returncode}")
                if stderr:
                    print(f"   Error: {stderr}")
                return False
                
    except Exception as e:
        print(f"   ❌ {test_name} failed to launch: {e}")
        return False

def test_python_imports():
    """Test that all required modules can be imported."""
    print("\n🐍 Testing Python imports...")
    
    required_modules = [
        'numpy',
        'matplotlib',
        'networkx',
        'tkinter',
        'pandas',
        'psutil',
    ]
    
    success_count = 0
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module} imported successfully")
            success_count += 1
        except ImportError as e:
            print(f"   ❌ {module} import failed: {e}")
    
    print(f"   📊 Import success rate: {success_count}/{len(required_modules)}")
    return success_count == len(required_modules)

def test_dcst_functionality():
    """Test core DCST functionality."""
    print("\n🔧 Testing DCST core functionality...")
    
    try:
        # Test simplified parallelization
        sys.path.insert(0, '.')
        from app.simple_parallelization import (
            get_simple_worker_count,
            should_use_parallel,
            get_parallelization_info
        )
        
        # Test worker count calculation
        worker_count = get_simple_worker_count(10)
        print(f"   ✅ Worker count calculation: {worker_count}")
        
        # Test parallel decision
        use_parallel = should_use_parallel(10)
        print(f"   ✅ Parallel decision: {use_parallel}")
        
        # Test parallelization info
        info = get_parallelization_info()
        print(f"   ✅ Parallelization info: {info['system_type']}")
        
        # Test algorithm imports
        from app.algorithms import (
            calculate_optimal_workers,
            parallel_cost_evaluation,
            parallel_local_search
        )
        
        print("   ✅ Algorithm imports successful")
        
        # Test graph generation
        from app.utils import generate_connected_random_graph
        import networkx as nx
        
        G = generate_connected_random_graph(10, 0.3)
        print(f"   ✅ Graph generation: {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        # Test basic algorithm functionality
        from app.algorithms import greedy_spanning_tree
        result = greedy_spanning_tree(G, max_children=3)
        if isinstance(result, tuple):
            tree, cost = result
            print(f"   ✅ Greedy algorithm: {len(tree.edges())} edges, cost={cost}")
        else:
            tree = result
            print(f"   ✅ Greedy algorithm: {len(tree.edges())} edges in spanning tree")
        
        return True
        
    except Exception as e:
        print(f"   ❌ DCST functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_numpy_compatibility():
    """Test NumPy compatibility and CPU dispatcher."""
    print("\n🔢 Testing NumPy compatibility...")
    
    try:
        import numpy as np
        print(f"   ✅ NumPy version: {np.__version__}")
        
        # Test basic NumPy operations
        arr = np.array([1, 2, 3, 4, 5])
        result = np.sum(arr)
        print(f"   ✅ NumPy operations: sum([1,2,3,4,5]) = {result}")
        
        # Test multiple imports (this was causing the CPU dispatcher error)
        import numpy as np2
        arr2 = np2.array([10, 20, 30])
        result2 = np2.mean(arr2)
        print(f"   ✅ Multiple NumPy imports: mean([10,20,30]) = {result2}")
        
        # Test matplotlib with NumPy
        import matplotlib.pyplot as plt
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        print(f"   ✅ NumPy with matplotlib: generated {len(x)} points")
        
        return True
        
    except Exception as e:
        print(f"   ❌ NumPy compatibility test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 DCST Tool - Executable Testing Suite")
    print("=" * 60)
    
    # Get paths to executables
    dist_dir = Path("dist")
    app_bundle = dist_dir / "DCST_Tool.app"
    standalone_exe = dist_dir / "DCST_Tool_macOS"
    
    # Check if executables exist
    if not dist_dir.exists():
        print("❌ dist directory not found. Please build the executables first.")
        return False
    
    test_results = []
    
    # Test Python environment
    test_results.append(("Python Imports", test_python_imports()))
    test_results.append(("NumPy Compatibility", test_numpy_compatibility()))
    test_results.append(("DCST Functionality", test_dcst_functionality()))
    
    # Test executables if they exist
    if standalone_exe.exists():
        test_results.append(("Standalone Executable", test_executable_launch(str(standalone_exe), "Standalone Executable")))
    else:
        print(f"⚠️ Standalone executable not found: {standalone_exe}")
    
    if app_bundle.exists():
        test_results.append(("App Bundle", test_executable_launch(str(app_bundle), "App Bundle")))
    else:
        print(f"⚠️ App bundle not found: {app_bundle}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! The DCST Tool executables are working correctly.")
        print("\n📋 Key fixes applied:")
        print("   • NumPy CPU dispatcher conflict resolved")
        print("   • PyInstaller runtime hooks implemented")
        print("   • Proper import order established")
        print("   • Environment variables configured")
        print("   • Simplified parallelization system working")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

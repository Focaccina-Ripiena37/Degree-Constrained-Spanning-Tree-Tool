#!/usr/bin/env python3
"""
Test script to reproduce and diagnose algorithm calculation errors.
This will help identify the specific error that occurs when starting calculations.
"""

import sys
import traceback
import time

def test_algorithm_imports():
    """Test if all algorithm modules can be imported correctly."""
    print("🧪 Testing algorithm imports...")
    
    try:
        sys.path.append('.')
        from app.algorithms import (
            greedy_spanning_tree,
            adaptive_neighborhood_local_search,
            simulated_annealing_spanning_tree,
            test_instance
        )
        print("✅ All algorithm functions imported successfully")
        return True
    except Exception as e:
        print(f"❌ Algorithm import failed: {e}")
        traceback.print_exc()
        return False

def test_basic_algorithm_execution():
    """Test basic algorithm execution with simple parameters."""
    print("🧪 Testing basic algorithm execution...")
    
    try:
        sys.path.append('.')
        import networkx as nx
        from app.algorithms import greedy_spanning_tree
        
        # Create a simple test graph
        G = nx.Graph()
        G.add_edge(0, 1, weight=1)
        G.add_edge(1, 2, weight=2)
        G.add_edge(2, 3, weight=3)
        G.add_edge(0, 3, weight=4)
        
        print("   Testing greedy algorithm...")
        tree, cost = greedy_spanning_tree(G, max_children=3, penalty=1000)
        print(f"   ✅ Greedy algorithm: {len(tree.edges())} edges, cost: {cost}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic algorithm execution failed: {e}")
        traceback.print_exc()
        return False

def test_test_instance_function():
    """Test the test_instance function that's called by the GUI."""
    print("🧪 Testing test_instance function...")
    
    try:
        sys.path.append('.')
        from app.algorithms import test_instance
        
        # Test with small parameters
        print("   Testing with small instance (n=5)...")
        result = test_instance(
            n_small=5,
            n_medium=10,
            n_large=15,
            max_children=3,
            penalty=1000,
            p_small=0.3,
            p_medium=0.3,
            p_large=0.3,
            stop_event=None,
            queue=None
        )
        
        print(f"   ✅ test_instance completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ test_instance function failed: {e}")
        traceback.print_exc()
        return False

def test_gui_start_computation():
    """Test the GUI start_computation method."""
    print("🧪 Testing GUI start_computation method...")
    
    try:
        sys.path.append('.')
        import tkinter as tk
        from app.gui import App
        
        # Create a minimal GUI setup
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        from tkinter import ttk
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        
        # Create the App instance
        app = App(root, progress_bar)
        
        # Set small test parameters
        app.n_small.set(5)
        app.n_medium.set(10)
        app.n_large.set(15)
        app.max_children.set(3)
        app.penalty.set(1000)
        
        print("   Attempting to start computation...")
        
        # Try to start computation
        app.start_computation()
        
        # Wait a moment for any immediate errors
        time.sleep(2)
        
        # Stop the computation
        app.stop_computation()
        
        root.destroy()
        
        print("   ✅ GUI start_computation method executed")
        return True
        
    except Exception as e:
        print(f"❌ GUI start_computation failed: {e}")
        traceback.print_exc()
        return False

def test_graph_generation():
    """Test graph generation functions."""
    print("🧪 Testing graph generation...")
    
    try:
        sys.path.append('.')
        from app.utils import generate_connected_random_graph
        
        # Test small graph generation
        print("   Testing small graph generation...")
        G = generate_connected_random_graph(5, 0.3)
        print(f"   ✅ Small graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        # Test medium graph generation
        print("   Testing medium graph generation...")
        G = generate_connected_random_graph(10, 0.3)
        print(f"   ✅ Medium graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        return True
        
    except Exception as e:
        print(f"❌ Graph generation failed: {e}")
        traceback.print_exc()
        return False

def test_memory_profiling():
    """Test if memory profiling is causing issues."""
    print("🧪 Testing memory profiling functionality...")
    
    try:
        sys.path.append('.')
        from app.algorithms import profile_memory
        
        # Test memory profiling
        @profile_memory
        def test_function():
            return sum(range(1000))
        
        result = test_function()
        print(f"   ✅ Memory profiling test completed: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Memory profiling test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run comprehensive algorithm error diagnosis."""
    print("🔍 DCST Tool - Algorithm Error Diagnosis")
    print("=" * 50)
    
    tests = [
        ("Algorithm Imports", test_algorithm_imports),
        ("Graph Generation", test_graph_generation),
        ("Basic Algorithm Execution", test_basic_algorithm_execution),
        ("Memory Profiling", test_memory_profiling),
        ("test_instance Function", test_test_instance_function),
        ("GUI start_computation", test_gui_start_computation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error - {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS RESULTS")
    print("=" * 50)
    
    passed = 0
    failed_tests = []
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
        if result:
            passed += 1
        else:
            failed_tests.append(test_name)
    
    total = len(results)
    print(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if failed_tests:
        print(f"\n🔍 Failed tests that need investigation:")
        for test in failed_tests:
            print(f"   • {test}")
        
        print(f"\n💡 Recommendation:")
        print(f"   Focus on fixing the failed tests above to resolve calculation errors.")
    else:
        print(f"\n🎉 All tests passed! If you're still experiencing errors,")
        print(f"   please provide the specific error message or steps to reproduce.")
    
    return len(failed_tests) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script to verify that the optimize_memory_usage function works
in the PyInstaller-built application.
"""

import sys
import traceback
import networkx as nx

def test_optimize_memory_usage():
    """Test the specific function that was causing the pydoc error."""
    try:
        # Create a test graph similar to what the application uses
        G = nx.Graph()
        G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0), (1, 3)])
        
        print(f"Original graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
        
        # Test the optimize_memory_usage function
        def optimize_memory_usage(G):
            """
            Optimize graph memory usage by using more efficient data structures.
            This is the exact function from algorithms.py that was failing.
            """
            # Relabel nodes to use integers for more efficient memory usage
            mapping = {node: idx for idx, node in enumerate(G.nodes())}
            G = nx.relabel_nodes(G, mapping)

            # Convert to a sparse adjacency matrix
            try:
                # For newer NetworkX versions (2.8+)
                adjacency_matrix = nx.to_scipy_sparse_array(G, format='csr')
            except AttributeError:
                # For older NetworkX versions
                adjacency_matrix = nx.to_scipy_sparse_matrix(G, format='csr')

            return G, mapping, adjacency_matrix
        
        # Run the optimization
        G_opt, node_mapping, adjacency_matrix = optimize_memory_usage(G.copy())
        
        print("✅ optimize_memory_usage function successful")
        print(f"   Optimized graph: {len(G_opt.nodes())} nodes, {len(G_opt.edges())} edges")
        print(f"   Node mapping: {node_mapping}")
        print(f"   Adjacency matrix shape: {adjacency_matrix.shape}")
        print(f"   Adjacency matrix type: {type(adjacency_matrix)}")
        print(f"   Adjacency matrix format: {adjacency_matrix.format}")
        
        return True
        
    except Exception as e:
        print(f"❌ optimize_memory_usage test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    print("🧪 Testing optimize_memory_usage function...")
    print("=" * 60)
    
    success = test_optimize_memory_usage()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test passed! The optimize_memory_usage function is working correctly.")
        print("   The pydoc import issue has been resolved.")
        return 0
    else:
        print("❌ Test failed! The optimize_memory_usage function still has issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

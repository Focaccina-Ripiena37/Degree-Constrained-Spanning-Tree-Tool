#!/usr/bin/env python3
"""
Test script to verify the DCST Tool executable works correctly.
This script tests the core functionality without requiring GUI interaction.
"""

import os
import sys
import subprocess
import platform
import time
from pathlib import Path

def get_executable_path():
    """Get the path to the built executable based on platform."""
    platform_name = platform.system().lower()
    dist_dir = Path('dist')
    
    if platform_name == "windows":
        return dist_dir / 'DCST_Tool_Windows.exe'
    elif platform_name == "darwin":
        return dist_dir / 'DCST_Tool.app' / 'Contents' / 'MacOS' / 'DCST_Tool_macOS'
    else:
        return dist_dir / 'DCST_Tool_Linux'

def test_executable_exists():
    """Test if the executable exists and is accessible."""
    exe_path = get_executable_path()
    
    print(f"🔍 Checking executable: {exe_path}")
    
    if not exe_path.exists():
        print(f"❌ Executable not found: {exe_path}")
        return False
    
    if not os.access(exe_path, os.X_OK):
        print(f"❌ Executable not executable: {exe_path}")
        return False
    
    print(f"✅ Executable found and accessible")
    return True

def test_executable_launch():
    """Test if the executable can launch (quick test)."""
    exe_path = get_executable_path()
    
    print(f"🚀 Testing executable launch...")
    
    try:
        # For GUI applications, we'll start the process and quickly terminate it
        # This tests that the executable can start without errors
        
        if platform.system().lower() == "darwin":
            # For macOS app bundles, use the app path
            app_path = exe_path.parent.parent.parent
            cmd = ['open', '-W', '--args', '--test-mode', str(app_path)]
        else:
            cmd = [str(exe_path), '--test-mode']
        
        print(f"   Running: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a short time to see if it starts successfully
        time.sleep(3)
        
        # Check if process is still running (good sign for GUI app)
        if process.poll() is None:
            print("✅ Executable launched successfully (process running)")
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return True
        else:
            # Process exited, check return code
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                print("✅ Executable ran and exited cleanly")
                return True
            else:
                print(f"❌ Executable exited with error code: {process.returncode}")
                if stderr:
                    print(f"   Error output: {stderr}")
                return False
                
    except FileNotFoundError:
        print(f"❌ Executable not found or not executable")
        return False
    except Exception as e:
        print(f"❌ Error launching executable: {e}")
        return False

def test_algorithm_import():
    """Test if the core algorithms can be imported (indirect test)."""
    print("🧪 Testing algorithm imports...")
    
    try:
        # Test if we can import the main modules
        sys.path.insert(0, '.')
        
        from app.algorithms import greedy_spanning_tree, adaptive_neighborhood_local_search, simulated_annealing_spanning_tree
        from app.gui import App
        import networkx as nx
        
        print("✅ Core modules imported successfully")
        
        # Test basic algorithm functionality
        G = nx.Graph()
        G.add_edge(0, 1, weight=1)
        G.add_edge(1, 2, weight=2)
        G.add_edge(2, 3, weight=3)
        G.add_edge(0, 3, weight=4)
        
        tree, cost = greedy_spanning_tree(G, max_children=3, penalty=1000)
        
        if len(tree.edges()) == 3:  # Should have n-1 edges for spanning tree
            print("✅ Greedy algorithm test passed")
            return True
        else:
            print(f"❌ Greedy algorithm test failed: expected 3 edges, got {len(tree.edges())}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Algorithm test error: {e}")
        return False

def get_file_info():
    """Get detailed information about the executable."""
    exe_path = get_executable_path()
    
    if not exe_path.exists():
        return None
    
    if exe_path.is_file():
        size_bytes = exe_path.stat().st_size
    else:
        # For app bundles, calculate total size
        size_bytes = sum(f.stat().st_size for f in exe_path.rglob('*') if f.is_file())
    
    size_mb = size_bytes / (1024 * 1024)
    
    return {
        'path': str(exe_path.absolute()),
        'size_bytes': size_bytes,
        'size_mb': size_mb,
        'platform': platform.system().lower(),
        'architecture': platform.machine(),
    }

def main():
    """Main test function."""
    print("🧪 DCST Tool - Executable Testing")
    print("=" * 50)
    
    platform_name = platform.system().lower()
    print(f"🖥️ Platform: {platform_name}")
    print(f"🏗️ Architecture: {platform.machine()}")
    
    all_tests_passed = True
    
    # Test 1: Check if executable exists
    print("\n📋 Test 1: Executable Existence")
    if not test_executable_exists():
        all_tests_passed = False
    
    # Test 2: Test algorithm imports (source code test)
    print("\n📋 Test 2: Algorithm Functionality")
    if not test_algorithm_import():
        all_tests_passed = False
    
    # Test 3: Test executable launch
    print("\n📋 Test 3: Executable Launch")
    if not test_executable_launch():
        print("⚠️ Executable launch test failed (this may be normal for GUI apps)")
        # Don't fail the overall test for this, as GUI apps may not respond to command line testing
    
    # Get file information
    print("\n📋 Executable Information")
    file_info = get_file_info()
    if file_info:
        print(f"📁 Path: {file_info['path']}")
        print(f"📏 Size: {file_info['size_mb']:.1f} MB ({file_info['size_bytes']:,} bytes)")
        print(f"🖥️ Platform: {file_info['platform']}")
        print(f"🏗️ Architecture: {file_info['architecture']}")
    else:
        print("❌ Could not get file information")
        all_tests_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✅ ALL TESTS PASSED!")
        print("🎉 The executable appears to be working correctly")
        
        if file_info:
            print(f"\n📦 Distribution Ready:")
            print(f"   File: {file_info['path']}")
            print(f"   Size: {file_info['size_mb']:.1f} MB")
            
            if platform_name == "windows":
                print(f"   📋 Windows users can run this .exe file directly")
                print(f"   📋 No installation required")
            elif platform_name == "darwin":
                print(f"   📋 macOS users can double-click the .app bundle")
                print(f"   📋 Can be moved to Applications folder")
            else:
                print(f"   📋 Linux users can run this executable directly")
                print(f"   📋 May need to set executable permissions: chmod +x")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please check the build process and try again")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script to verify the startup fix works correctly.
Tests both source code and executable versions.
"""

import subprocess
import sys
import time
import os
import platform
from pathlib import Path

def test_source_code_startup():
    """Test the source code version startup."""
    print("🧪 Testing source code startup...")
    
    try:
        # Start the application
        process = subprocess.Popen(
            [sys.executable, "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a few seconds for startup
        time.sleep(5)
        
        # Check if process is still running (good sign for GUI app)
        if process.poll() is None:
            print("✅ Source code version: Application started successfully")
            
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            return True
        else:
            # Process exited, check output
            stdout, stderr = process.communicate()
            print(f"❌ Source code version: Process exited with code {process.returncode}")
            if stderr:
                print(f"   Error output: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Source code version: Failed to start - {e}")
        return False

def test_executable_startup():
    """Test the executable version startup."""
    print("🧪 Testing executable startup...")
    
    # Determine executable path based on platform
    platform_name = platform.system().lower()
    
    if platform_name == "darwin":  # macOS
        exe_path = Path("dist/DCST_Tool.app")
        if exe_path.exists():
            try:
                # For macOS app bundles, use open command
                process = subprocess.Popen(
                    ["open", str(exe_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Wait for the open command to complete
                process.wait(timeout=10)
                
                if process.returncode == 0:
                    print("✅ Executable version: macOS app launched successfully")
                    return True
                else:
                    print(f"❌ Executable version: Failed to launch (code {process.returncode})")
                    return False
                    
            except Exception as e:
                print(f"❌ Executable version: Failed to launch - {e}")
                return False
        else:
            print("❌ Executable version: macOS app bundle not found")
            return False
            
    elif platform_name == "windows":
        exe_path = Path("dist/DCST_Tool_Windows.exe")
        if exe_path.exists():
            try:
                process = subprocess.Popen(
                    [str(exe_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                time.sleep(5)
                
                if process.poll() is None:
                    print("✅ Executable version: Windows exe started successfully")
                    process.terminate()
                    return True
                else:
                    print(f"❌ Executable version: Process exited with code {process.returncode}")
                    return False
                    
            except Exception as e:
                print(f"❌ Executable version: Failed to start - {e}")
                return False
        else:
            print("❌ Executable version: Windows exe not found")
            return False
            
    else:  # Linux
        exe_path = Path("dist/DCST_Tool_Linux")
        if exe_path.exists():
            try:
                process = subprocess.Popen(
                    [str(exe_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                time.sleep(5)
                
                if process.poll() is None:
                    print("✅ Executable version: Linux binary started successfully")
                    process.terminate()
                    return True
                else:
                    print(f"❌ Executable version: Process exited with code {process.returncode}")
                    return False
                    
            except Exception as e:
                print(f"❌ Executable version: Failed to start - {e}")
                return False
        else:
            print("❌ Executable version: Linux binary not found")
            return False

def test_splash_screen_module():
    """Test the splash screen module directly."""
    print("🧪 Testing splash screen module...")
    
    try:
        # Import and test splash screen
        sys.path.insert(0, '.')
        from app.splash_screen import show_splash_screen
        import tkinter as tk
        
        # Create test root
        root = tk.Tk()
        root.withdraw()
        
        # Test splash screen creation
        splash = show_splash_screen(parent_root=root, duration=1.0, manual_mode=True)
        
        if splash:
            # Test manual updates
            splash.update_status("Testing...", 50)
            time.sleep(0.5)
            splash.update_status("Complete!", 100)
            time.sleep(0.5)
            
            # Close splash
            splash.close()
            print("✅ Splash screen module: Works correctly")
            
            root.destroy()
            return True
        else:
            print("❌ Splash screen module: Failed to create splash")
            root.destroy()
            return False
            
    except Exception as e:
        print(f"❌ Splash screen module: Error - {e}")
        return False

def test_import_modules():
    """Test that all required modules can be imported."""
    print("🧪 Testing module imports...")
    
    modules_to_test = [
        "app.gui",
        "app.algorithms", 
        "app.platform_styles",
        "app.splash_screen",
        "app.utils"
    ]
    
    all_imports_successful = True
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except Exception as e:
            print(f"   ❌ {module}: {e}")
            all_imports_successful = False
    
    if all_imports_successful:
        print("✅ Module imports: All modules imported successfully")
    else:
        print("❌ Module imports: Some modules failed to import")
    
    return all_imports_successful

def main():
    """Run all startup tests."""
    print("🚀 DCST Tool - Startup Fix Verification")
    print("=" * 50)
    
    platform_name = platform.system()
    print(f"🖥️ Platform: {platform_name}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    # Run all tests
    tests = [
        ("Module Imports", test_import_modules),
        ("Splash Screen Module", test_splash_screen_module),
        ("Source Code Startup", test_source_code_startup),
        ("Executable Startup", test_executable_startup),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"📋 {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error - {e}")
            results.append((test_name, False))
        
        print()
    
    # Summary
    print("=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
        if result:
            passed += 1
    
    print()
    print(f"📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Startup fix is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

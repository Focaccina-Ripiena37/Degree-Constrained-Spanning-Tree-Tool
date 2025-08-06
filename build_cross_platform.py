#!/usr/bin/env python3
"""
Cross-platform build script for DCST Tool.
Automatically detects the platform and builds the appropriate executable.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def detect_platform():
    """Detect the current platform and return build information."""
    system = platform.system().lower()
    
    if system == "windows":
        return {
            'name': 'Windows',
            'script': 'build_windows.py',
            'executable': 'dist/DCST_Tool_Windows.exe',
            'description': 'Windows executable (.exe)'
        }
    elif system == "darwin":
        return {
            'name': 'macOS',
            'script': 'build_macos.py',
            'executable': 'dist/DCST_Tool.app',
            'description': 'macOS app bundle (.app)'
        }
    elif system == "linux":
        return {
            'name': 'Linux',
            'script': 'build_executables.py',  # Use the general script for Linux
            'executable': 'dist/DCST_Tool_Linux',
            'description': 'Linux executable'
        }
    else:
        return {
            'name': system,
            'script': 'build_executables.py',  # Fallback to general script
            'executable': f'dist/DCST_Tool_{system}',
            'description': f'{system} executable'
        }

def check_requirements():
    """Check if all requirements are met for building."""
    print("🔍 Checking build requirements...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check if pip is available
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
        print("✅ pip is available")
    except subprocess.CalledProcessError:
        print("❌ pip is not available")
        return False
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    print("✅ requirements.txt found")
    
    return True

def install_project_dependencies():
    """Install project dependencies from requirements.txt."""
    print("📦 Installing project dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True, text=True)
        print("✅ Project dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_platform_build(platform_info):
    """Run the platform-specific build script."""
    script_path = Path(platform_info['script'])
    
    if not script_path.exists():
        print(f"❌ Build script not found: {script_path}")
        return False
    
    print(f"🚀 Running {platform_info['name']} build script...")
    
    try:
        # Run the platform-specific build script
        result = subprocess.run([sys.executable, str(script_path)], 
                              check=True, text=True)
        print(f"✅ {platform_info['name']} build completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {platform_info['name']} build failed: {e}")
        return False

def verify_build_output(platform_info):
    """Verify that the build output was created successfully."""
    executable_path = Path(platform_info['executable'])
    
    if executable_path.exists():
        if executable_path.is_file():
            size_mb = executable_path.stat().st_size / (1024 * 1024)
        else:
            # For app bundles, calculate total size
            size_bytes = sum(f.stat().st_size for f in executable_path.rglob('*') if f.is_file())
            size_mb = size_bytes / (1024 * 1024)
        
        print(f"✅ Build output verified: {executable_path}")
        print(f"📏 Size: {size_mb:.1f} MB")
        return True
    else:
        print(f"❌ Build output not found: {executable_path}")
        return False

def show_distribution_info(platform_info):
    """Show platform-specific distribution information."""
    print("\n" + "=" * 60)
    print("📋 DISTRIBUTION INFORMATION")
    print("=" * 60)
    
    if platform_info['name'] == 'Windows':
        print("🖥️ Windows Distribution:")
        print("   • Executable: DCST_Tool_Windows.exe")
        print("   • Completely portable - no installation required")
        print("   • Compatible with Windows 10/11")
        print("   • May trigger antivirus scan (normal for unsigned executables)")
        print("   • Supports Windows dark/light theme detection")
        
    elif platform_info['name'] == 'macOS':
        print("🍎 macOS Distribution:")
        print("   • App Bundle: DCST_Tool.app")
        print("   • Drag to Applications folder to install")
        print("   • Requires macOS 10.14 or later")
        print("   • Supports macOS dark/light mode")
        print("   • Optimized for Retina displays")
        print("   • May show security warning on first run (normal)")
        
    elif platform_info['name'] == 'Linux':
        print("🐧 Linux Distribution:")
        print("   • Executable: DCST_Tool_Linux")
        print("   • May need executable permissions: chmod +x DCST_Tool_Linux")
        print("   • Run with: ./DCST_Tool_Linux")
        print("   • Compatible with most Linux distributions")
        
    print(f"\n📁 Location: {Path(platform_info['executable']).absolute()}")

def main():
    """Main cross-platform build process."""
    print("🚀 DCST Tool - Cross-Platform Build System")
    print("=" * 60)
    
    # Detect platform
    platform_info = detect_platform()
    print(f"🖥️ Platform detected: {platform_info['name']}")
    print(f"📦 Target: {platform_info['description']}")
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements check failed")
        return False
    
    # Install project dependencies
    if not install_project_dependencies():
        print("❌ Failed to install project dependencies")
        return False
    
    # Run platform-specific build
    if not run_platform_build(platform_info):
        print("❌ Platform build failed")
        return False
    
    # Verify build output
    if not verify_build_output(platform_info):
        print("❌ Build verification failed")
        return False
    
    # Show distribution information
    show_distribution_info(platform_info)
    
    print("\n" + "=" * 60)
    print("✅ CROSS-PLATFORM BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 Your DCST Tool executable is ready for distribution!")
        print("📖 See the distribution information above for deployment instructions.")
    else:
        print("\n💥 Build failed. Please check the error messages above.")
    
    sys.exit(0 if success else 1)

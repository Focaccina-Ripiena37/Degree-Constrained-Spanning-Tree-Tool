#!/usr/bin/env python3
"""
Windows-specific build script for creating optimized DCST Tool executable.
Optimized for Windows 10/11 with enhanced performance and compatibility.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def check_windows_environment():
    """Check if we're running on Windows and verify requirements."""
    if platform.system() != "Windows":
        print("❌ This script is designed for Windows only")
        return False
    
    print(f"✅ Windows {platform.release()} detected")
    print(f"🏗️ Architecture: {platform.machine()}")
    return True

def install_windows_dependencies():
    """Install Windows-specific build dependencies."""
    print("📦 Installing Windows build dependencies...")
    
    dependencies = [
        "pyinstaller>=6.0.0",
        "setuptools",
        "wheel",
        "pywin32",  # Windows-specific
        "pywin32-ctypes",  # Windows-specific
    ]
    
    for dep in dependencies:
        print(f"   Installing {dep}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True, text=True)
            print(f"   ✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {dep}: {e}")
            return False
    
    return True

def create_windows_spec():
    """Create Windows-optimized PyInstaller spec file."""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
# Windows-optimized PyInstaller spec for DCST Tool

import os
import sys
from pathlib import Path

# Get the directory containing this spec file
spec_dir = Path(SPECPATH)
project_root = spec_dir

# Define data files to include
datas = [
    (str(project_root / 'app' / 'github.png'), 'app'),
    (str(project_root / 'icon.ico'), '.'),
    (str(project_root / 'icon.ico'), 'app'),
]

# Windows-specific hidden imports
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.figure',
    'matplotlib.pyplot',
    'networkx',
    'pandas',
    'numpy',
    'scipy',
    'psutil',
    'memory_profiler',
    'tabulate',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'tqdm',
    'queue',
    'threading',
    'multiprocessing',
    'concurrent.futures',
    'json',
    'csv',
    'pickle',
    'gzip',
    'zipfile',
    'tempfile',
    'logging',
    'datetime',
    'time',
    'random',
    'math',
    'heapq',
    'collections',
    'itertools',
    'functools',
    'operator',
    'copy',
    're',
    'os',
    'sys',
    'pathlib',
    # Windows-specific
    'win32api',
    'win32con',
    'win32gui',
    'win32process',
    'pywintypes',
]

# Analysis configuration
a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test',
        'tests',
        'pytest',
        'unittest',
        'doctest',
        'pdb',
        'pydoc',
        'IPython',
        'jupyter',
        'notebook',
        # Exclude macOS/Linux specific modules
        'AppKit',
        'Foundation',
        'objc',
        'PyObjC',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove unnecessary files to reduce size
a.datas = [x for x in a.datas if not any(exclude in x[0].lower() for exclude in [
    'test', 'example', 'demo', 'doc', 'readme', 'license', 'changelog'
])]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Windows executable configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DCST_Tool_Windows',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'icon.ico'),
    version_file=None,  # Could add version info here
    uac_admin=False,  # Don't require admin privileges
    uac_uiaccess=False,
)
'''
    
    with open('dcst_tool_windows.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ Windows PyInstaller spec file created: dcst_tool_windows.spec")
    return True

def build_windows_executable():
    """Build the Windows executable using PyInstaller."""
    print("🔨 Building Windows executable...")
    
    # Clean previous builds
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   🧹 Cleaned previous {dir_name} directory")
    
    # Run PyInstaller
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "dcst_tool_windows.spec"]
        print(f"   Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("   ✅ PyInstaller completed successfully")
        
        # Print any warnings
        if result.stderr:
            print("   ⚠️ Warnings:")
            for line in result.stderr.split('\n'):
                if line.strip() and 'WARNING' in line:
                    print(f"      {line}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ PyInstaller failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False

def main():
    """Main Windows build process."""
    print("🚀 DCST Tool - Windows Build Script")
    print("=" * 50)
    
    # Check environment
    if not check_windows_environment():
        return False
    
    print(f"🐍 Python version: {sys.version}")
    
    # Install dependencies
    if not install_windows_dependencies():
        print("❌ Failed to install Windows dependencies")
        return False
    
    # Create spec file
    if not create_windows_spec():
        print("❌ Failed to create Windows spec file")
        return False
    
    # Build executable
    if not build_windows_executable():
        print("❌ Failed to build Windows executable")
        return False
    
    # Check result
    exe_path = Path('dist/DCST_Tool_Windows.exe')
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        
        print("\n" + "=" * 50)
        print("✅ WINDOWS BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print(f"📁 Executable location: {exe_path.absolute()}")
        print(f"📏 File size: {size_mb:.1f} MB")
        print(f"🖥️ Platform: Windows")
        
        print("\n📋 Windows Distribution Notes:")
        print("   • The .exe file is completely portable")
        print("   • No installation required")
        print("   • Compatible with Windows 10/11")
        print("   • May trigger antivirus scan (normal for unsigned executables)")
        print("   • Optimized for Windows dark/light theme detection")
        
        print(f"\n🧪 Test the executable: {exe_path.absolute()}")
        return True
    else:
        print(f"❌ Executable not found at: {exe_path.absolute()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

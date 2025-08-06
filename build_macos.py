#!/usr/bin/env python3
"""
macOS-specific build script for creating optimized DCST Tool app bundle.
Optimized for macOS with proper dark mode support and native styling.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def check_macos_environment():
    """Check if we're running on macOS and verify requirements."""
    if platform.system() != "Darwin":
        print("❌ This script is designed for macOS only")
        return False
    
    print(f"✅ macOS {platform.release()} detected")
    print(f"🏗️ Architecture: {platform.machine()}")
    
    # Check for Xcode command line tools
    try:
        subprocess.run(['xcode-select', '--version'], check=True, capture_output=True)
        print("✅ Xcode command line tools available")
    except subprocess.CalledProcessError:
        print("⚠️ Xcode command line tools not found (may affect some features)")
    
    return True

def install_macos_dependencies():
    """Install macOS-specific build dependencies."""
    print("📦 Installing macOS build dependencies...")

    dependencies = [
        "pyinstaller>=6.0.0",
        "setuptools",
        "wheel",
        "pyobjc-framework-Cocoa",  # macOS-specific
        "pyobjc-framework-Quartz",  # macOS-specific
        "numpy>=1.21.0",  # Ensure compatible NumPy version
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

def create_macos_spec():
    """Create macOS-optimized PyInstaller spec file."""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
# macOS-optimized PyInstaller spec for DCST Tool

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

# macOS-specific hidden imports
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
    'subprocess',
    # macOS-specific
    'Foundation',
    'AppKit',
    'Cocoa',
    'objc',
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
        # Exclude Windows/Linux specific modules
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'pywintypes',
        'pywin32',
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

# macOS executable configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DCST_Tool_macOS',
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
)

# Create macOS app bundle with enhanced configuration
app = BUNDLE(
    exe,
    name='DCST_Tool.app',
    icon=str(project_root / 'icon.ico'),
    bundle_identifier='com.dcst.tool',
    info_plist={
        'CFBundleName': 'DCST Tool',
        'CFBundleDisplayName': 'Degree-Constrained Spanning Tree Tool',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.dcst.tool',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
        'CFBundleDocumentTypes': [],
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
        'NSRequiresAquaSystemAppearance': False,  # Allow dark mode
        'NSSupportsAutomaticGraphicsSwitching': True,
        'LSUIElement': False,  # Show in dock
        'NSPrincipalClass': 'NSApplication',
        'CFBundleExecutable': 'DCST_Tool_macOS',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'DCST',
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': False,
            'NSExceptionDomains': {}
        },
        'NSCameraUsageDescription': 'This app does not use the camera.',
        'NSMicrophoneUsageDescription': 'This app does not use the microphone.',
        'NSLocationUsageDescription': 'This app does not use location services.',
    },
)
'''
    
    with open('dcst_tool_macos.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ macOS PyInstaller spec file created: dcst_tool_macos.spec")
    return True

def build_macos_executable():
    """Build the macOS app bundle using PyInstaller."""
    print("🔨 Building macOS app bundle with NumPy fixes...")

    # Set NumPy environment variables for build process
    os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'

    # Clean previous builds
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   🧹 Cleaned previous {dir_name} directory")
    
    # Run PyInstaller
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "dcst_tool_macos.spec"]
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
    """Main macOS build process."""
    print("🚀 DCST Tool - macOS Build Script")
    print("=" * 50)
    
    # Check environment
    if not check_macos_environment():
        return False
    
    print(f"🐍 Python version: {sys.version}")
    
    # Install dependencies
    if not install_macos_dependencies():
        print("❌ Failed to install macOS dependencies")
        return False
    
    # Create spec file
    if not create_macos_spec():
        print("❌ Failed to create macOS spec file")
        return False
    
    # Build executable
    if not build_macos_executable():
        print("❌ Failed to build macOS app bundle")
        return False
    
    # Check result
    app_path = Path('dist/DCST_Tool.app')
    if app_path.exists():
        # Calculate total size of app bundle
        size_bytes = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file())
        size_mb = size_bytes / (1024 * 1024)
        
        print("\n" + "=" * 50)
        print("✅ MACOS BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print(f"📁 App bundle location: {app_path.absolute()}")
        print(f"📏 Bundle size: {size_mb:.1f} MB")
        print(f"🖥️ Platform: macOS")
        
        print("\n📋 macOS Distribution Notes:")
        print("   • The .app bundle can be distributed as-is")
        print("   • Users can drag it to Applications folder")
        print("   • Requires macOS 10.14 or later")
        print("   • Supports both light and dark mode")
        print("   • May show security warning on first run (normal)")
        print("   • Optimized for Retina displays")
        
        print(f"\n🧪 Test the app bundle: open {app_path.absolute()}")
        return True
    else:
        print(f"❌ App bundle not found at: {app_path.absolute()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

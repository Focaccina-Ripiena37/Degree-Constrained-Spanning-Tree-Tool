#!/usr/bin/env python3
"""
Build script for creating portable standalone executables for the DCST Tool.
Supports both Windows (.exe) and macOS platforms.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def get_platform_info():
    """Get current platform information."""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if system == "windows":
        return "windows", "exe"
    elif system == "darwin":
        return "macos", "app"
    elif system == "linux":
        return "linux", "bin"
    else:
        return system, "bin"

def install_build_dependencies():
    """Install required build dependencies."""
    print("📦 Installing build dependencies...")
    
    dependencies = [
        "pyinstaller>=6.0.0",
        "setuptools",
        "wheel"
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

def create_pyinstaller_spec():
    """Create PyInstaller spec file for the application."""
    
    platform_name, ext = get_platform_info()
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

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
    (str(project_root / 'icon.ico'), 'app'),  # Also include in app directory for easier access
]

# Define hidden imports (modules that PyInstaller might miss)
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
]

# Analysis configuration
a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
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

# Platform-specific executable configuration
if sys.platform.startswith('win'):
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
        console=False,  # Set to False for GUI app
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(project_root / 'icon.ico'),
    )
elif sys.platform.startswith('darwin'):
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
        console=False,  # Set to False for GUI app
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    # Create macOS app bundle
    app = BUNDLE(
        exe,
        name='DCST_Tool.app',
        icon=str(project_root / 'icon.ico'),  # Use the icon file
        bundle_identifier='com.dcst.tool',
        info_plist={{
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
            'NSSupportsAutomaticGraphicsSwitching': True,  # Support GPU switching
            'LSUIElement': False,  # Show in dock
            'NSPrincipalClass': 'NSApplication',
            'CFBundleExecutable': 'DCST_Tool_macOS',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'DCST',
        }},
    )
else:
    # Linux and other platforms
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='DCST_Tool_Linux',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
'''
    
    with open('dcst_tool.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ PyInstaller spec file created: dcst_tool.spec")
    return True

def build_executable():
    """Build the executable using PyInstaller."""
    platform_name, ext = get_platform_info()
    
    print(f"🔨 Building executable for {platform_name}...")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("   🧹 Cleaned previous build directory")
    
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("   🧹 Cleaned previous dist directory")
    
    # Run PyInstaller
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "dcst_tool.spec"]
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

def get_executable_info():
    """Get information about the created executable."""
    platform_name, ext = get_platform_info()
    
    dist_dir = Path('dist')
    
    if platform_name == "windows":
        exe_path = dist_dir / 'DCST_Tool_Windows.exe'
    elif platform_name == "macos":
        exe_path = dist_dir / 'DCST_Tool.app'
    else:
        exe_path = dist_dir / 'DCST_Tool_Linux'
    
    if exe_path.exists():
        if exe_path.is_file():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
        else:
            # For app bundles, calculate total size
            size_bytes = sum(f.stat().st_size for f in exe_path.rglob('*') if f.is_file())
            size_mb = size_bytes / (1024 * 1024)
        
        return {
            'path': str(exe_path.absolute()),
            'size_mb': size_mb,
            'platform': platform_name,
            'exists': True
        }
    else:
        return {
            'path': str(exe_path.absolute()),
            'size_mb': 0,
            'platform': platform_name,
            'exists': False
        }

def main():
    """Main build process."""
    print("🚀 DCST Tool - Executable Builder")
    print("=" * 50)
    
    platform_name, ext = get_platform_info()
    print(f"🖥️ Target platform: {platform_name}")
    print(f"🐍 Python version: {sys.version}")
    
    # Step 1: Install build dependencies
    if not install_build_dependencies():
        print("❌ Failed to install build dependencies")
        return False
    
    # Step 2: Create PyInstaller spec file
    if not create_pyinstaller_spec():
        print("❌ Failed to create spec file")
        return False
    
    # Step 3: Build executable
    if not build_executable():
        print("❌ Failed to build executable")
        return False
    
    # Step 4: Get executable information
    exe_info = get_executable_info()
    
    print("\n" + "=" * 50)
    print("✅ BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    
    if exe_info['exists']:
        print(f"📁 Executable location: {exe_info['path']}")
        print(f"📏 File size: {exe_info['size_mb']:.1f} MB")
        print(f"🖥️ Platform: {exe_info['platform']}")
        
        if platform_name == "macos":
            print("\n📋 macOS Distribution Notes:")
            print("   • The .app bundle can be distributed as-is")
            print("   • Users can drag it to Applications folder")
            print("   • Requires macOS 10.14 or later")
            print("   • May show security warning on first run (normal)")
        elif platform_name == "windows":
            print("\n📋 Windows Distribution Notes:")
            print("   • The .exe file is completely portable")
            print("   • No installation required")
            print("   • Compatible with Windows 10/11")
            print("   • May trigger antivirus scan (normal for unsigned executables)")
        
        print(f"\n🧪 Test the executable by running: {exe_info['path']}")
        
    else:
        print(f"❌ Executable not found at expected location: {exe_info['path']}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

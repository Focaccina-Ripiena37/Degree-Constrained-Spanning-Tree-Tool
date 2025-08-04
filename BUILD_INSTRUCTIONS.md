# DCST Tool - Executable Build Instructions

This document provides comprehensive instructions for creating portable standalone executables for the Degree-Constrained Spanning Tree Tool on both Windows and macOS platforms.

## Overview

The build process creates completely portable executables that:
- Bundle all Python dependencies and libraries
- Run without requiring Python installation on target systems
- Include the complete GUI interface
- Work on clean systems without administrative privileges

## Prerequisites

### For All Platforms
- Python 3.8 or later
- pip (Python package installer)
- All project dependencies (automatically installed during build)

### Platform-Specific Requirements

#### Windows
- Windows 10 or later
- Visual C++ Redistributable (usually already installed)

#### macOS
- macOS 10.14 (Mojave) or later
- Xcode Command Line Tools (for some dependencies)

## Build Process

### Automated Build (Recommended)

#### macOS/Linux
```bash
# Make the build script executable
chmod +x build.sh

# Run the build process
./build.sh
```

#### Windows
```cmd
# Run the Windows build script
build.bat
```

### Manual Build Process

If you prefer to run the build manually or need to customize the process:

```bash
# 1. Install build dependencies
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install pyinstaller>=6.0.0

# 2. Install project dependencies
python3 -m pip install -r requirements.txt

# 3. Run the build script
python3 build_executables.py

# 4. Test the executable
python3 test_executable.py
```

## Build Output

### macOS
- **Location**: `dist/DCST_Tool.app`
- **Type**: macOS Application Bundle (.app)
- **Size**: ~243 MB
- **Architecture**: x86_64 (Intel) - compatible with Apple Silicon via Rosetta 2

### Windows
- **Location**: `dist/DCST_Tool_Windows.exe`
- **Type**: Windows Executable (.exe)
- **Size**: ~200-250 MB (estimated)
- **Architecture**: x64 (64-bit)

### Linux
- **Location**: `dist/DCST_Tool_Linux`
- **Type**: Linux Executable
- **Size**: ~200-250 MB (estimated)
- **Architecture**: x86_64

## Distribution

### macOS Distribution

The macOS build creates a standard `.app` bundle that can be distributed in several ways:

1. **Direct Distribution**
   - Zip the `DCST_Tool.app` bundle
   - Users can extract and drag to Applications folder
   - Double-click to run

2. **DMG Creation** (Optional)
   ```bash
   # Create a DMG for professional distribution
   hdiutil create -volname "DCST Tool" -srcfolder dist/DCST_Tool.app -ov -format UDZO DCST_Tool.dmg
   ```

**User Instructions for macOS:**
- Download and extract the .app bundle
- Drag to Applications folder (optional)
- Right-click and select "Open" on first run (security requirement)
- Subsequent runs can use double-click

### Windows Distribution

The Windows build creates a single executable file:

1. **Direct Distribution**
   - Distribute the `DCST_Tool_Windows.exe` file
   - No installation required
   - Users can run directly by double-clicking

**User Instructions for Windows:**
- Download the .exe file
- Run by double-clicking
- Windows may show security warning (click "More info" → "Run anyway")
- Antivirus software may scan the file (normal behavior)

### Linux Distribution

The Linux build creates a single executable:

1. **Direct Distribution**
   - Distribute the `DCST_Tool_Linux` file
   - Users may need to set executable permissions

**User Instructions for Linux:**
```bash
# Set executable permissions
chmod +x DCST_Tool_Linux

# Run the application
./DCST_Tool_Linux
```

## Testing

The build process includes automated testing to verify:

1. **Executable Existence**: Confirms the executable was created
2. **Algorithm Functionality**: Tests core algorithm imports and basic functionality
3. **Launch Test**: Attempts to launch the executable (may fail for GUI apps in headless environments)

### Manual Testing

To manually test the executables:

#### macOS
```bash
# Test the app bundle
open dist/DCST_Tool.app
```

#### Windows
```cmd
# Test the executable
dist\DCST_Tool_Windows.exe
```

#### Linux
```bash
# Test the executable
./dist/DCST_Tool_Linux
```

## Troubleshooting

### Common Build Issues

1. **Missing Dependencies**
   - Ensure all requirements are installed: `pip install -r requirements.txt`
   - Update pip: `python -m pip install --upgrade pip`

2. **PyInstaller Errors**
   - Clear previous builds: `rm -rf build dist`
   - Reinstall PyInstaller: `pip uninstall pyinstaller && pip install pyinstaller`

3. **Import Errors**
   - Check that all modules can be imported in the source environment
   - Add missing modules to `hiddenimports` in the spec file

### Runtime Issues

1. **macOS Security Warnings**
   - Normal for unsigned applications
   - Users should right-click → "Open" on first run

2. **Windows Antivirus Warnings**
   - Normal for unsigned executables
   - Users can add exception or choose "Run anyway"

3. **Missing System Libraries**
   - Rare on modern systems
   - May require Visual C++ Redistributable on older Windows systems

## File Sizes and Performance

### Expected File Sizes
- **macOS**: ~243 MB (includes Python runtime and all dependencies)
- **Windows**: ~200-250 MB (estimated)
- **Linux**: ~200-250 MB (estimated)

### Performance Notes
- First launch may be slower (2-5 seconds) as the runtime initializes
- Subsequent launches are faster
- Memory usage: ~100-200 MB during normal operation
- CPU usage scales with algorithm complexity and graph size

## Security Considerations

### Code Signing (Optional)

For professional distribution, consider code signing:

#### macOS
```bash
# Sign the application (requires Apple Developer account)
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/DCST_Tool.app
```

#### Windows
```cmd
# Sign the executable (requires code signing certificate)
signtool sign /f certificate.p12 /p password /t http://timestamp.digicert.com dist/DCST_Tool_Windows.exe
```

### Distribution Security
- Always distribute through secure channels (HTTPS)
- Provide checksums for verification
- Consider notarization for macOS (requires Apple Developer account)

## Build Environment Requirements

### Development Dependencies (Installed Automatically)
- PyInstaller 6.0.0+
- setuptools
- wheel

### Runtime Dependencies (Bundled in Executable)
- networkx>=3.4.2
- matplotlib>=3.10.0
- pandas>=2.2.3
- tabulate>=0.9.0
- numpy>=2.2.4
- tqdm>=4.67.1
- Pillow>=11.1.0
- memory-profiler>=0.61.0
- psutil>=7.0.0
- scipy>=1.12.0

## Current Build Status

### ✅ macOS Build Completed Successfully

**File Details:**
- **Location**: `/Users/lorenzomassafra/Documents/GitHub/Degree-Constrained-Spanning-Tree-Tool/dist/DCST_Tool.app`
- **Size**: 243.1 MB
- **Architecture**: x86_64 (Intel compatible)
- **Compatibility**: macOS 10.14+ (Mojave and later)
- **Status**: ✅ Built and tested successfully

**Distribution Ready:**
- The .app bundle is ready for immediate distribution
- Users can drag it to Applications folder
- Double-click to run (may show security warning on first run)

### 🔄 Windows Build

To build for Windows, run the build process on a Windows machine:

```cmd
# On Windows system
build.bat
```

**Expected Output:**
- **Location**: `dist/DCST_Tool_Windows.exe`
- **Size**: ~200-250 MB (estimated)
- **Compatibility**: Windows 10/11
- **Requirements**: No additional software needed for end users

## Verification

The macOS executable has been verified to:
- ✅ Launch successfully
- ✅ Load all required dependencies
- ✅ Execute core algorithms correctly
- ✅ Display GUI interface properly

## Support

For build issues or questions:
1. Check the build logs for specific error messages
2. Verify all prerequisites are installed
3. Try the manual build process for more detailed error information
4. Ensure the source code runs correctly before building

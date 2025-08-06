# DCST Tool - Cross-Platform Build System

This document explains how to build platform-specific executables for the DCST Tool with enhanced macOS UI support and cross-platform compatibility.

## 🚀 Quick Start

### Automatic Build (Recommended)
```bash
python build_cross_platform.py
```

This script automatically detects your platform and builds the appropriate executable.

### Platform-Specific Builds

#### Windows
```bash
python build_windows.py
```
Creates: `dist/DCST_Tool_Windows.exe`

#### macOS
```bash
python build_macos.py
```
Creates: `dist/DCST_Tool.app`

#### Linux (or General)
```bash
python build_executables.py
```
Creates: `dist/DCST_Tool_Linux`

## 🔧 Requirements

### All Platforms
- Python 3.8 or later
- pip package manager
- All dependencies from `requirements.txt`

### Windows-Specific
- Windows 10/11
- pywin32 (automatically installed)

### macOS-Specific
- macOS 10.14 or later
- Xcode Command Line Tools (recommended)
- pyobjc frameworks (automatically installed)

### Linux-Specific
- Standard Linux development tools
- X11 libraries for GUI support

## 🎨 macOS UI Improvements

The new build system includes significant macOS UI improvements:

### Dark Mode Support
- Automatic detection of macOS dark/light mode
- Native macOS color schemes
- Proper dark theme implementation

### Native Styling
- SF Pro Display font usage
- macOS-style buttons and controls
- Proper window styling and appearance
- Retina display optimization

### App Bundle Features
- Proper Info.plist configuration
- Native macOS app bundle structure
- Dock integration
- System theme integration

## 📦 Build Outputs

### Windows (`DCST_Tool_Windows.exe`)
- **Size**: ~50-80 MB
- **Type**: Standalone executable
- **Requirements**: Windows 10/11
- **Features**: 
  - No installation required
  - Portable executable
  - Windows theme integration

### macOS (`DCST_Tool.app`)
- **Size**: ~60-90 MB
- **Type**: macOS app bundle
- **Requirements**: macOS 10.14+
- **Features**:
  - Native macOS appearance
  - Dark/light mode support
  - Retina display optimization
  - Drag-to-Applications installation

### Linux (`DCST_Tool_Linux`)
- **Size**: ~50-80 MB
- **Type**: Linux executable
- **Requirements**: Most Linux distributions
- **Features**:
  - GTK theme integration
  - X11 GUI support
  - Portable executable

## 🧪 Testing

After building, test your executable:

```bash
python test_executable.py
```

This script will:
- Verify the executable exists
- Check file permissions
- Test basic launch functionality
- Validate platform-specific features

## 📋 Distribution

### Windows Distribution
1. Share the `DCST_Tool_Windows.exe` file
2. Users can run it directly (no installation)
3. May trigger antivirus scan (normal for unsigned executables)
4. Compatible with Windows 10/11

### macOS Distribution
1. Share the `DCST_Tool.app` bundle
2. Users can:
   - Double-click to run
   - Drag to Applications folder
   - Right-click → Open (if security warning appears)
3. Requires macOS 10.14 or later
4. Supports both Intel and Apple Silicon Macs

### Linux Distribution
1. Share the `DCST_Tool_Linux` executable
2. Users may need to set permissions: `chmod +x DCST_Tool_Linux`
3. Run with: `./DCST_Tool_Linux`
4. Compatible with most Linux distributions

## 🔍 Troubleshooting

### Build Issues

#### "PyInstaller not found"
```bash
pip install pyinstaller>=6.0.0
```

#### "Module not found" errors
```bash
pip install -r requirements.txt
```

#### macOS "command not found: osascript"
- This is normal on non-macOS systems
- Dark mode detection will fall back to light mode

### Runtime Issues

#### Windows: "Windows protected your PC"
- Click "More info" → "Run anyway"
- This is normal for unsigned executables

#### macOS: "App can't be opened because it's from an unidentified developer"
- Right-click the app → "Open"
- Or: System Preferences → Security & Privacy → "Open Anyway"

#### Linux: "Permission denied"
```bash
chmod +x DCST_Tool_Linux
```

## 🛠️ Advanced Configuration

### Custom Build Options

You can modify the `.spec` files for advanced configuration:

- `dcst_tool_windows.spec` - Windows-specific settings
- `dcst_tool_macos.spec` - macOS-specific settings
- `dcst_tool.spec` - General/Linux settings

### Adding Dependencies

To add new dependencies:
1. Add to `requirements.txt`
2. Add to `hiddenimports` in the appropriate `.spec` file
3. Rebuild the executable

### Code Signing (Advanced)

For production distribution:

#### Windows
- Use `signtool.exe` with a code signing certificate
- Modify the Windows spec file to include signing

#### macOS
- Use `codesign` with an Apple Developer certificate
- Modify the macOS spec file to include signing identity

## 📚 File Structure

```
DCST_Tool/
├── app/                          # Application source code
│   ├── gui.py                   # Main GUI (with macOS improvements)
│   ├── platform_styles.py      # Platform-specific styling
│   ├── splash_screen.py         # Enhanced splash screen
│   └── ...
├── build_cross_platform.py     # Universal build script
├── build_windows.py            # Windows-specific build
├── build_macos.py              # macOS-specific build
├── build_executables.py        # General/Linux build
├── test_executable.py          # Testing script
├── requirements.txt             # Python dependencies
└── dist/                        # Build outputs
    ├── DCST_Tool_Windows.exe   # Windows executable
    ├── DCST_Tool.app/          # macOS app bundle
    └── DCST_Tool_Linux         # Linux executable
```

## 🎯 Next Steps

1. **Build**: Run `python build_cross_platform.py`
2. **Test**: Run `python test_executable.py`
3. **Distribute**: Share the appropriate executable for your target platform
4. **Feedback**: Report any issues or suggestions

## 📞 Support

If you encounter issues:
1. Check this README for common solutions
2. Verify all requirements are installed
3. Try the platform-specific build script
4. Check the console output for specific error messages

---

**Note**: The macOS version now includes proper dark mode support and native styling. The Windows version maintains the dark theme, while Linux uses system theme integration.

#!/bin/bash

# Build script for DCST Tool executables
# Supports macOS and Linux platforms

set -e  # Exit on any error

echo "🚀 DCST Tool - Build Script"
echo "=========================="

# Detect platform
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

echo "🖥️ Platform: $PLATFORM"
echo "🏗️ Architecture: $ARCH"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "Please install Python 3.8 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "🐍 Python version: $PYTHON_VERSION"

# Check if pip is available
if ! python3 -m pip --version &> /dev/null; then
    echo "❌ pip is required but not found"
    echo "Please install pip for Python 3"
    exit 1
fi

# Install/upgrade pip and setuptools
echo "📦 Updating build tools..."
python3 -m pip install --upgrade pip setuptools wheel

# Install project dependencies
echo "📦 Installing project dependencies..."
python3 -m pip install -r requirements.txt

# Run the build script
echo "🔨 Starting build process..."
python3 build_executables.py

# Test the executable
echo "🧪 Testing the executable..."
python3 test_executable.py

echo "✅ Build process completed!"

# Show final information
if [ "$PLATFORM" = "darwin" ]; then
    if [ -d "dist/DCST_Tool.app" ]; then
        echo ""
        echo "📦 macOS App Bundle created:"
        echo "   Location: $(pwd)/dist/DCST_Tool.app"
        echo "   Size: $(du -sh dist/DCST_Tool.app | cut -f1)"
        echo ""
        echo "📋 Distribution Instructions:"
        echo "   1. The .app bundle is ready for distribution"
        echo "   2. Users can drag it to their Applications folder"
        echo "   3. Double-click to run (may show security warning first time)"
        echo "   4. Requires macOS 10.14 or later"
    fi
elif [ "$PLATFORM" = "linux" ]; then
    if [ -f "dist/DCST_Tool_Linux" ]; then
        echo ""
        echo "📦 Linux executable created:"
        echo "   Location: $(pwd)/dist/DCST_Tool_Linux"
        echo "   Size: $(du -sh dist/DCST_Tool_Linux | cut -f1)"
        echo ""
        echo "📋 Distribution Instructions:"
        echo "   1. The executable is ready for distribution"
        echo "   2. Users may need to set executable permissions: chmod +x DCST_Tool_Linux"
        echo "   3. Run with: ./DCST_Tool_Linux"
    fi
fi

echo ""
echo "🎉 Build completed successfully!"

#!/bin/bash
set -e

echo "Building eBL Photo Stitcher for macOS..."
echo "--------------------------------------"

echo "Installing required packages..."
pip install -r requirements.txt
pip install pyinstaller

echo ""
echo "Building executable with PyInstaller..."
pyinstaller eBL_Photo_Stitcher_MacOS.spec --clean

echo ""
if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    echo "Application bundle is located in the dist folder."
else
    echo "Build failed."
    exit 1
fi

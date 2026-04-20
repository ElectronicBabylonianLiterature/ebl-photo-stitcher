#!/bin/bash
set -e

echo "Building eBL Photo Stitcher for macOS..."
echo "--------------------------------------"

echo "Installing required packages..."
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

echo ""
echo "Building executable with PyInstaller..."
python3 -m PyInstaller eBL_Photo_Stitcher_MacOS.spec --clean

echo ""
echo "Build completed successfully!"
echo "Application bundle is located in the dist folder."

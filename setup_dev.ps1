# Setup script for eBL Photo Stitcher development environment

# Stop on errors
$ErrorActionPreference = "Stop"

Write-Host "Setting up development environment for eBL Photo Stitcher" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green

# Check Python version
$pythonVersion = python --version
Write-Host "Using $pythonVersion" -ForegroundColor Cyan

# Create virtual environment if it doesn't exist
if (-not (Test-Path -Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment. Aborting." -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Install requirements
Write-Host "Installing required packages..." -ForegroundColor Cyan
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install requirements. See error above." -ForegroundColor Red
    exit 1
}

# Test pyexiv2 installation
Write-Host "`nTesting pyexiv2 installation..." -ForegroundColor Cyan
python tools\test_pyexiv2.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "pyexiv2 test failed. See error above." -ForegroundColor Yellow
    Write-Host "Some metadata features may not be available." -ForegroundColor Yellow
    Write-Host "See docs/pyexiv2_install.md for installation instructions." -ForegroundColor Yellow
} else {
    Write-Host "pyexiv2 is working correctly." -ForegroundColor Green
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "You can now run the application with: python gui_app.py" -ForegroundColor Green

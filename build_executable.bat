@echo off
echo Building eBL Photo Stitcher executable...
echo --------------------------------------
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Building executable with PyInstaller...
pyinstaller eBL_Photo_Stitcher.spec --clean

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build completed successfully!
    echo Executable is located in the dist folder.
) else (
    echo Build failed with error %ERRORLEVEL%.
)

pause

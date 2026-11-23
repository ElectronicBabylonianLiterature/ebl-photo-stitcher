# -*- mode: python ; coding: utf-8 -*-

import os
import subprocess
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

pyexiv2_datas, pyexiv2_binaries, pyexiv2_hiddenimports = collect_all("pyexiv2")
block_cipher = None

# These packages call importlib.metadata at import time, which fails in the
# frozen app ("No package metadata was found for ...") unless the dist-info is bundled.
METADATA_PACKAGES = [
    "imageio",
    "rembg",
    "pymatting",
    "onnxruntime",
    "numpy",
    "scikit-image",
    "pooch",
    "tqdm",
    "requests",
    "pillow",
    "opencv-python",
    "rawpy",
    "piexif",
    "cairosvg",
]


def collect_metadata(packages):
    datas = []
    for package in packages:
        try:
            datas += copy_metadata(package)
        except Exception:
            print(f"WARNING: no metadata found for {package}, skipping.")
    return datas


metadata_datas = collect_metadata(METADATA_PACKAGES)

def get_homebrew_prefix():
    """Get the Homebrew prefix path (/usr/local or /opt/homebrew)."""
    try:
        prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
        return prefix
    except (subprocess.CalledProcessError, FileNotFoundError):
        if os.path.exists('/opt/homebrew'):
            return '/opt/homebrew'
        return '/usr/local'

def get_cairo_dependencies():
    prefix = get_homebrew_prefix()
    main_lib_path = Path(prefix) / 'lib' / 'libcairo.2.dylib'

    if not main_lib_path.exists():
        print(f"WARNING: libcairo.2.dylib not found at {main_lib_path}. SVG support will likely fail.")
        return []

    def find_deps(file_path):
        deps = set()
        try:
            output = subprocess.check_output(['otool', '-L', str(file_path)], text=True)
            for line in output.splitlines()[1:]:
                dep_path_str = line.strip().split(' ')[0]
                if dep_path_str.startswith(prefix):
                    deps.add(dep_path_str)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return deps

    all_deps = {str(main_lib_path.resolve())}
    processed_deps = set()
    while True:
        new_deps_to_check = all_deps - processed_deps
        if not new_deps_to_check:
            break
        for dep in new_deps_to_check:
            found = find_deps(dep)
            all_deps.update(found)
            processed_deps.add(dep)
    return [(dep, '.') for dep in all_deps]

cairo_binaries = get_cairo_dependencies()

a = Analysis(
    ["gui_app.py"],
    pathex=["./lib"],
    binaries=pyexiv2_binaries + cairo_binaries,
    datas=[
        ("assets", "assets"),
        ("lib", "lib"),
    ]
    + pyexiv2_datas
    + metadata_datas,
    hiddenimports=[
        "cv2",
        "numpy",
        "imageio",
        "rawpy",
        "piexif",
        "cairosvg",
        "rembg",
        "onnxruntime",
    ]
    + pyexiv2_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="eBL Photo Stitcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="eBL Photo Stitcher",
)

app = BUNDLE(
    coll,
    name="eBL Photo Stitcher.app",
    icon="eBL_Logo.icns",
    bundle_identifier="com.yourcompany.ebl-photo-stitcher",
    version="1.0.0",
    info_plist={
        "CFBundleName": "eBL Photo Stitcher",
        "CFBundleDisplayName": "eBL Photo Stitcher",
        "CFBundleIdentifier": "com.yourcompany.ebl-photo-stitcher",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "EBLS",
        "CFBundleExecutable": "eBL Photo Stitcher",
        "CFBundleIconFile": "eBL_Logo.icns",
        "LSMinimumSystemVersion": "10.13.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "LSApplicationCategoryType": "public.app-category.photography",
        "NSCameraUsageDescription": "This app needs camera access for photo processing.",
        "NSPhotoLibraryUsageDescription": "This app needs photo library access to process images.",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Images",
                "CFBundleTypeRole": "Editor",
                "LSItemContentTypes": [
                    "public.image",
                    "public.jpeg",
                    "public.png",
                    "public.tiff",
                    "com.adobe.raw-image",
                ],
                "LSHandlerRank": "Alternate",
            }
        ],
    },
)


def create_dmg():
    """Create a DMG file from the app bundle."""
    app_name = "eBL Photo Stitcher"
    app_bundle = f"dist/{app_name}.app"
    dmg_name = f"dist/{app_name}-Installer.dmg"
    temp_dmg = f"dist/{app_name}-temp.dmg"
    volume_name = f"{app_name} Installer"

    if os.path.exists(dmg_name):
        os.remove(dmg_name)
    if os.path.exists(temp_dmg):
        os.remove(temp_dmg)

    try:
        result = subprocess.run(
            ["du", "-sm", app_bundle], capture_output=True, text=True, check=True
        )
        app_size = int(result.stdout.split()[0])
        dmg_size = max(app_size + 50, 200)
        print(f"Creating DMG with size: {dmg_size}MB")

        subprocess.run(
            [
                "hdiutil",
                "create",
                "-size",
                f"{dmg_size}m",
                "-fs",
                "HFS+",
                "-volname",
                volume_name,
                temp_dmg,
            ],
            check=True,
        )

        result = subprocess.run(
            ["hdiutil", "attach", temp_dmg, "-readwrite", "-noverify"],
            capture_output=True,
            text=True,
            check=True,
        )

        mount_point = None
        for line in result.stdout.split("\n"):
            if "/Volumes/" in line:
                mount_point = line.split("\t")[-1].strip()
                break

        if not mount_point:
            raise Exception("Could not find mount point")

        print(f"Mounted DMG at: {mount_point}")

        subprocess.run(["cp", "-R", app_bundle, mount_point], check=True)

        subprocess.run(
            ["ln", "-s", "/Applications", f"{mount_point}/Applications"], check=True
        )

        bg_folder = f"{mount_point}/.background"
        os.makedirs(bg_folder, exist_ok=True)

        applescript = f"""
        tell application "Finder"
            tell disk "{volume_name}"
                open
                set current view of container window to icon view
                set toolbar visible of container window to false
                set statusbar visible of container window to false
                set the bounds of container window to {{100, 100, 600, 400}}
                set viewOptions to the icon view options of container window
                set arrangement of viewOptions to not arranged
                set icon size of viewOptions to 128
                set position of item "{app_name}.app" of container window to {{150, 200}}
                set position of item "Applications" of container window to {{350, 200}}
                close
                open
                update without registering applications
                delay 2
            end tell
        end tell
        """

        subprocess.run(["osascript", "-e", applescript], check=True)

        subprocess.run(["hdiutil", "detach", mount_point], check=True)

        subprocess.run(
            [
                "hdiutil",
                "convert",
                temp_dmg,
                "-format",
                "UDZO",
                "-imagekey",
                "zlib-level=9",
                "-o",
                dmg_name,
            ],
            check=True,
        )

        os.remove(temp_dmg)

        print(f"DMG created successfully: {dmg_name}")

    except subprocess.CalledProcessError as e:
        print(f"Error creating DMG: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise


def create_pkg():
    """Create a PKG installer as an alternative to DMG."""
    app_name = "eBL Photo Stitcher"
    app_bundle = f"dist/{app_name}.app"
    pkg_name = f"dist/{app_name}-Installer.pkg"

    try:
        if os.path.exists(pkg_name):
            os.remove(pkg_name)

        subprocess.run(
            [
                "pkgbuild",
                "--root",
                "dist",
                "--identifier",
                "com.yourcompany.ebl-photo-stitcher",
                "--version",
                "1.0.0",
                "--install-location",
                "/Applications",
                pkg_name,
            ],
            check=True,
        )

        print(f"PKG created successfully: {pkg_name}")

    except subprocess.CalledProcessError as e:
        print(f"Error creating PKG: {e}")
        raise


if __name__ == "__main__":
    import sys

    if sys.platform != "darwin":
        print("Warning: This spec file is designed for macOS")
        sys.exit(1)

    try:
        create_dmg()
    except Exception as e:
        print(f"DMG creation failed: {e}")
        print("Attempting to create PKG instead...")
        try:
            create_pkg()
        except Exception as pkg_e:
            print(f"PKG creation also failed: {pkg_e}")
            print("App bundle created successfully, but installer creation failed.")
            print(
                f"You can manually distribute the app bundle: dist/eBL Photo Stitcher.app"
            )

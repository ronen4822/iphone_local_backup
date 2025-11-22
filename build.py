"""Build script to create executable using PyInstaller"""
import PyInstaller.__main__
import sys
from pathlib import Path

def build_executable():
    """Build the executable using PyInstaller"""

    # Get the project root directory
    project_root = Path(__file__).parent
    main_script = project_root / "main.py"

    # PyInstaller arguments
    args = [
        str(main_script),
        '--name=iPhoneMediaBackup',
        '--onefile',
        '--windowed',  # No console window
        '--clean',

        # Add application icon (optional, can be added later)
        # '--icon=icon.ico',

        # Include hidden imports that PyInstaller might miss
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=customtkinter',
        '--hidden-import=pymobiledevice3',
        '--hidden-import=pymobiledevice3.services.afc',
        '--hidden-import=pymobiledevice3.services.lockdown',
        '--hidden-import=contextvars',

        # Collect all data files from customtkinter
        '--collect-data=customtkinter',

        # Add the src directory to the Python path
        f'--paths={project_root / "src"}',

        # Output directory
        f'--distpath={project_root / "dist"}',
        f'--workpath={project_root / "build"}',
        f'--specpath={project_root}',

        # Optimization
        '--optimize=2',

        # Add metadata
        '--version-file=version_info.txt' if (project_root / 'version_info.txt').exists() else '',
    ]

    # Remove empty strings
    args = [arg for arg in args if arg]

    print("Building executable with PyInstaller...")
    print(f"Arguments: {args}")

    try:
        PyInstaller.__main__.run(args)
        print("\n" + "="*60)
        print("Build completed successfully!")
        print(f"Executable location: {project_root / 'dist' / 'iPhoneMediaBackup.exe'}")
        print("="*60)
    except Exception as e:
        print(f"\nBuild failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build_executable()

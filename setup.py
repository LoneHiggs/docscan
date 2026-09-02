#!/usr/bin/env python
"""
Setup script for DocScan macOS .app
"""
from setuptools import setup

APP = ['desktop_gui.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,
    'packages': ['cv2', 'numpy', 'PIL', 'tkinter'],
    'includes': ['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
    'excludes': ['matplotlib', 'scipy', 'pandas'],
    'iconfile': None,  # Add .icns file here if you have one
    'plist': {
        'CFBundleName': 'DocScan',
        'CFBundleDisplayName': 'DocScan',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

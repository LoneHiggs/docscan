# DocScan

A desktop application for enhancing document photos to improve text readability.

## Features

- Real-time image enhancement with live preview
- Background normalization and gamma correction
- Optional CLAHE, sharpening, and denoising
- Side-by-side Before/After comparison
- Batch processing with multiple output formats
- PDF export with configurable DPI (72/150/300/600)
- Drag-and-drop support
- Save/load settings

## Download

Download the latest release from the [Releases page](../../releases).

### macOS
Download `DocScan.app.zip`, unzip, and run the app.

### Windows
Download `DocScan.exe` and run it directly.

## Building from Source

### Prerequisites
- Python 3.10-3.13
- pip

### Install Dependencies
```bash
pip install opencv-python numpy Pillow tkinterdnd2 pyinstaller
```

### Build macOS App
```bash
pyinstaller docscan.spec --clean -y
```
The app will be in `dist/DocScan.app`.

### Build Windows Executable
```bash
pyinstaller --onefile --windowed --name DocScan desktop_gui.py
```
The executable will be in `dist/DocScan.exe`.

## Usage

1. Launch the app
2. Click "Open Image" or drag-and-drop an image file
3. Adjust parameters using the sliders
4. Click "Save Image" to export
5. Use "Show Before/After" to compare results

### Batch Processing
1. Click "Select Multiple Files" or "Select Folder"
2. Click "Process Batch"
3. Choose output format (PNG, JPEG, PDF, or ZIP)
4. Output is saved next to the source files

## Settings

Click "Save Settings" to save your current parameters. Settings are automatically loaded on app startup.

## License

MIT

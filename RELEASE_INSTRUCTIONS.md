# Procedure for Updating and Releasing DocScan

## 1. Make Code Changes
Make your edits to the source code (e.g., `desktop_gui.py`, `docscan.spec`, etc.).

## 2. Test Locally
Test the application before building:
```bash
cd /Users/benny/Sandbox/html/docscan
python3 desktop_gui.py
```

## 3. Update Version and Commit to Git
Commit your changes with a clear message:
```bash
git add <modified_files>
git commit -m "Descriptive commit message about the change"
git push origin main
```

## 4. Build the macOS .app
Clean and build with PyInstaller:
```bash
pyinstaller docscan.spec --clean -y
```

## 5. Remove Quarantine & Prepare ZIP for Distribution
Remove macOS quarantine attribute and create a properly structured ZIP (with symlinks preserved):
```bash
xattr -cr dist/DocScan.app
rm -f dist/DocScan.app.zip
cd dist && zip -r -y DocScan.app.zip DocScan.app && cd ..
```

## 6. Create/Update GitHub Release
Determine the next version number (increment patch/minor/major: v1.0.2 → v1.0.3).

Delete the old release if updating an existing version, then create a new one:
```bash
gh release delete <VERSION> --yes
gh release create <VERSION> dist/DocScan.app.zip --title "DocScan <VERSION>" --notes "Brief description of changes"
```

Example:
```bash
gh release delete v1.0.3 --yes
gh release create v1.0.3 dist/DocScan.app.zip --title "DocScan v1.0.3" --notes "Fix: description here"
```

## 7. Verify
The release URL will be printed. Test downloading the ZIP from a fresh download to ensure it works correctly.

## Notes
- Always zip from inside `dist/` directory with `-y` flag to preserve symlinks (critical for macOS apps)
- Run `xattr -cr` to remove quarantine attributes from the built app
- GitHub CLI (`gh`) must be authenticated
- For Windows builds, run on a Windows machine with: `pyinstaller --onefile --windowed --name DocScan desktop_gui.py`

# 4K Video Downloader - EXE Build Setup Guide

## Overview
This guide will help you convert your Python application into a Windows EXE file using GitHub Actions for automatic building.

---

## Step 1: Prepare Your Repository

### 1.1 Create a GitHub Repository
1. Go to [GitHub.com](https://github.com)
2. Click **New Repository**
3. Name it (e.g., `4k-video-downloader`)
4. Add description, choose Public or Private
5. Click **Create Repository**

### 1.2 Clone & Setup Locally
```bash
git clone https://github.com/YOUR_USERNAME/4k-video-downloader.git
cd 4k-video-downloader
```

---

## Step 2: Add Project Files

### 2.1 Copy Your Main Files
Copy these files to your repository root:
- ✅ `Index1.py` (your main application)
- ✅ `requirements.txt` (included in this guide)
- ✅ `.github/workflows/build_exe.yml` (workflow file - see Step 3)

### 2.2 Project Structure
```
4k-video-downloader/
├── Index1.py                    # Main application
├── requirements.txt              # Dependencies
├── app.ico                       # (Optional) Application icon
├── resources/                    # (Optional) Resource folder
├── .github/
│   └── workflows/
│       └── build_exe.yml        # GitHub Actions workflow
├── .gitignore
└── README.md
```

### 2.3 Create .gitignore
Create `.gitignore` file:
```
# Build artifacts
dist/
build/
*.egg-info/
__pycache__/
*.pyc

# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

---

## Step 3: Set Up GitHub Actions

### 3.1 Create Workflow Directory
```bash
mkdir -p .github/workflows
```

### 3.2 Add Workflow File
Create `.github/workflows/build_exe.yml` with the following content:

```yaml
name: Build Windows EXE

on:
  push:
    branches: [ main, master, develop ]
    tags:
      - 'v*'
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: ['3.11']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller

    - name: Build EXE with PyInstaller
      run: |
        pyinstaller --onefile ^
          --windowed ^
          --name "4K_Video_Downloader" ^
          --icon app.ico ^
          --add-data "resources;resources" ^
          Index1.py

    - name: Upload EXE as artifact
      uses: actions/upload-artifact@v3
      with:
        name: 4K_Video_Downloader
        path: dist/4K_Video_Downloader.exe

    - name: Create Release
      if: startsWith(github.ref, 'refs/tags/')
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        draft: false
        prerelease: false

    - name: Upload Release Asset
      if: startsWith(github.ref, 'refs/tags/')
      uses: actions/upload-release-asset@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        upload_url: ${{ steps.create_release.outputs.upload_url }}
        asset_path: ./dist/4K_Video_Downloader.exe
        asset_name: 4K_Video_Downloader.exe
        asset_content_type: application/octet-stream
```

---

## Step 4: Create requirements.txt

Create `requirements.txt` in repository root:
```
PySide6>=6.5.0
yt-dlp>=2023.12.0
requests>=2.31.0
```

---

## Step 5: Push to GitHub

### 5.1 Commit Files
```bash
git add .
git commit -m "Initial commit: Add application files and CI/CD workflow"
git branch -M main
git push -u origin main
```

### 5.2 Verify Workflow
1. Go to your GitHub repo
2. Click **Actions** tab
3. You should see "Build Windows EXE" workflow
4. It will auto-trigger on push

---

## Step 6: Build Triggers

### Automatic Builds Trigger On:
- ✅ **Push to main/master/develop branches**
- ✅ **Pull requests** to main/master
- ✅ **Tag creation** (e.g., `git tag v1.0.0` → creates GitHub Release)
- ✅ **Manual trigger** (Actions tab → Run workflow)

### 6.1 Create a Release (Manual Tag)
```bash
git tag v1.0.0
git push origin v1.0.0
```

This will:
1. Build the EXE
2. Create a GitHub Release
3. Auto-attach the EXE to the release

---

## Step 7: Download the Built EXE

### Option A: From Artifacts (Recommended for Testing)
1. Go to **Actions** tab
2. Click the completed workflow
3. Scroll to **Artifacts**
4. Download `4K_Video_Downloader`

### Option B: From GitHub Release
1. Go to **Releases** tab (if you created a tag)
2. Find your release
3. Download the EXE directly

---

## Optional Customizations

### Custom Application Icon
1. Create a 256x256 PNG image
2. Convert to ICO using online tool or:
```bash
pip install pillow
python -c "from PIL import Image; Image.open('icon.png').save('app.ico')"
```
3. Place `app.ico` in repository root

### Modify Executable Name
Edit the `--name` parameter in workflow:
```yaml
--name "MyAppName"
```

### Add Resources/Assets
If your app has resources folder:
```yaml
--add-data "resources;resources"
```

### Code Signing (Advanced)
Add to workflow for production releases:
```yaml
- name: Sign EXE
  run: |
    signtool sign /f cert.pfx /p ${{ secrets.CERT_PASSWORD }} dist/4K_Video_Downloader.exe
```

---

## Troubleshooting

### Build Fails - Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'xxx'`
**Fix**: Add the package to `requirements.txt`

### EXE Won't Start
**Error**: Application closes immediately
**Cause**: Missing dependencies or yt-dlp not found
**Fix**: 
- Install ffmpeg: https://ffmpeg.org/download.html
- Update yt-dlp: `pip install --upgrade yt-dlp`

### Antivirus Detects as Virus
**Cause**: PyInstaller binaries sometimes trigger false positives
**Fix**: 
- Submit to antivirus vendor for whitelisting
- Sign your executable (see Optional section)

### GitHub Action Timeout
**Cause**: Build takes >6 hours on free tier
**Fix**: Upgrade to GitHub Pro or optimize build

### File Not Found During Build
**Error**: `FileNotFoundError: app.ico not found`
**Fix**: 
- Remove `--icon app.ico` from workflow if you don't have it
- Or create a simple icon file

---

## Next Steps

1. ✅ Create GitHub repository
2. ✅ Add your files
3. ✅ Push to GitHub
4. ✅ Monitor Actions tab for build
5. ✅ Download your EXE!

---

## Useful Links
- **PyInstaller Docs**: https://pyinstaller.org/
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **yt-dlp**: https://github.com/yt-dlp/yt-dlp
- **PySide6 Docs**: https://doc.qt.io/qtforpython/

---

## Support
If you encounter issues:
1. Check the **Actions** tab for build logs
2. Review error messages carefully
3. Test locally first:
   ```bash
   pip install -r requirements.txt
   python Index1.py
   ```

Good luck! 🚀

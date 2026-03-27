# 4K Video Downloader

A feature-rich video downloader application with beautiful UI, dark/light themes, and support for multiple video platforms.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Build](https://img.shields.io/badge/Build-GitHub%20Actions-brightgreen)

## Features

✨ **Modern UI**
- Sleek dark and light themes
- Smooth animations and transitions
- Real-time progress tracking
- Video metadata display

🎥 **Video Support**
- Download from YouTube, TikTok, Instagram, and 1000+ platforms
- Multiple quality options (4K, 1080p, 720p, etc.)
- Audio-only extraction (MP3)
- Batch downloads with progress tracking

⚙️ **Advanced Features**
- Pause/Resume downloads
- Cancel downloads
- Customizable output directory
- Format selection (MP4, WebM, etc.)
- Detailed download statistics

## Quick Start

### Download EXE (Windows)
1. Go to [Releases](https://github.com/YOUR_USERNAME/4k-video-downloader/releases)
2. Download the latest `4K_Video_Downloader.exe`
3. Run the executable!

### Installation from Source

#### Prerequisites
- Python 3.11+
- ffmpeg (for audio extraction)
- yt-dlp (included in dependencies)

#### Setup
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/4k-video-downloader.git
cd 4k-video-downloader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python Index1.py
```

## Requirements

- **OS**: Windows 10+ (Linux/Mac support with minor modifications)
- **Python**: 3.11 or higher
- **RAM**: 500MB minimum
- **Disk Space**: 100MB for the application

## Dependencies

```
PySide6>=6.5.0          # GUI framework
yt-dlp>=2023.12.0       # Video downloading
requests>=2.31.0        # HTTP library
```

## Building EXE from Source

### Using PyInstaller Locally
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "4K_Video_Downloader" Index1.py
```

The executable will be in `dist/4K_Video_Downloader.exe`

### Using GitHub Actions (Automatic)
1. Push code to GitHub
2. Create a tag: `git tag v1.0.0 && git push origin v1.0.0`
3. GitHub Actions automatically builds the EXE
4. Download from [Releases](https://github.com/YOUR_USERNAME/4k-video-downloader/releases)

See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed instructions.

## Usage

1. **Paste URL**: Paste a video URL from supported platforms
2. **Select Quality**: Choose desired video quality
3. **Choose Format**: Select output format (MP4, WebM, etc.)
4. **Download**: Click download button
5. **Monitor**: Track progress in real-time

## Supported Platforms

The application supports 1000+ video hosting sites including:
- YouTube
- TikTok
- Instagram
- Twitter/X
- Facebook
- Dailymotion
- Vimeo
- And many more!

(Full list: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## Configuration

### Output Directory
Default: `~/Downloads`

Change in the application by clicking "Browse" button.

### Quality Settings
- **Best**: Highest available quality
- **4K (2160p)**: 4K resolution
- **1080p**: Full HD
- **720p**: HD
- **Audio Only**: MP3 extraction

### Format Selection
- MP4 (Most compatible)
- WebM (Better compression)
- MKV (Best quality)

## Screenshots

### Dark Theme
> [Coming soon]

### Light Theme
> [Coming soon]

## Troubleshooting

### Issue: "yt-dlp not found"
**Solution**:
```bash
pip install --upgrade yt-dlp
```

### Issue: "FFmpeg not installed"
**Solution**: 
- Windows: Download from https://ffmpeg.org/download.html
- Linux: `sudo apt install ffmpeg`
- Mac: `brew install ffmpeg`

### Issue: EXE won't start
**Solution**:
1. Run Command Prompt as Administrator
2. Navigate to download folder
3. Run: `4K_Video_Downloader.exe`
4. Check for error messages

### Issue: Download fails
**Solution**:
1. Check internet connection
2. Verify URL is correct and accessible
3. Update yt-dlp: `pip install --upgrade yt-dlp`
4. Try a different video

## Performance

- **Memory Usage**: 150-300MB typical
- **CPU Usage**: Low to medium during download
- **Download Speed**: Limited by your internet connection
- **Parallel Downloads**: 3-5 simultaneous downloads recommended

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|------------|
| OS | Windows 10 | Windows 11 |
| CPU | Dual Core | Quad Core |
| RAM | 4GB | 8GB+ |
| Storage | 100MB | 500MB+ |
| Network | 1Mbps | 10Mbps+ |

## Security & Privacy

- ✅ No tracking or telemetry
- ✅ No cloud synchronization
- ✅ All downloads stored locally
- ✅ Open source code (auditable)
- ✅ No account or registration required

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Disclaimer

This tool is for personal and educational use only. Ensure you have the right to download content from any platform you use it with. Users are responsible for complying with applicable laws and terms of service.

## Support

- 📧 Email: [your-email@example.com]
- 💬 Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/4k-video-downloader/issues)
- 📚 Wiki: [GitHub Wiki](https://github.com/YOUR_USERNAME/4k-video-downloader/wiki)

## Changelog

### v1.0.0 (Initial Release)
- ✅ Basic video downloading
- ✅ Multi-platform support
- ✅ Dark/Light themes
- ✅ Progress tracking
- ✅ Quality selection

## Credits

Built with:
- [PySide6](https://wiki.qt.io/Qt_for_Python) - Qt for Python
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloader
- [PyInstaller](https://pyinstaller.org/) - Python to EXE conversion

## Roadmap

- [ ] Linux build support
- [ ] Mac build support  
- [ ] Playlist downloads
- [ ] Download queue management
- [ ] Advanced filtering options
- [ ] Subtitle downloads
- [ ] Thumbnail extraction
- [ ] Settings persistence
- [ ] Auto-update feature

---

**Made with ❤️ by [Your Name]**

Last updated: 2024

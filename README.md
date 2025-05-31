# AutoGIF 🎬✨

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/yourusername/autogif)

Transform YouTube videos into stunning animated GIFs with perfectly-timed, stylized subtitles and eye-catching effects.

![AutoGIF Demo](docs/demo.gif)

## ✨ Features

- **Precise Video Clipping**: Extract exact segments from YouTube videos with millisecond accuracy
- **Automatic Transcription**: AI-powered subtitle generation with word-level timing
- **10+ Visual Effects**: Including typewriter, bounce, wave, rainbow, glitch, sparkle, and more
- **Matrix-Style UI**: Retro cyberpunk interface with neon green aesthetics
- **Offline Operation**: Works completely offline after initial video download
- **Cross-Platform**: Runs on Windows, macOS, and Linux

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- 4GB RAM minimum (8GB recommended)
- Internet connection (for downloading videos)

### Installation

#### Windows

```bash
git clone https://github.com/yourusername/autogif.git
cd autogif

# IMPORTANT: Run build.bat first to set up the environment
build.bat

# Then run the application
run.bat
```

#### macOS / Linux

```bash
git clone https://github.com/yourusername/autogif.git
cd autogif
chmod +x build.sh run.sh

# Build first (creates virtual environment)
./build.sh

# Then run the application
./run.sh
```

> **Note**: Always run the build script first! It creates the Python virtual environment and installs all dependencies.

## 📦 Included Binaries & Dependencies

### Windows Package Contents

The Windows release includes the following pre-compiled binaries in the `resources/` directory:

- **FFmpeg** (v6.0+) - LGPL-licensed video processing tools
  - `ffmpeg.exe` - Video/audio converter
  - `ffprobe.exe` - Media analyzer
  - `ffplay.exe` - Media player
- **yt-dlp** - Public domain YouTube downloader
- **Whisper** - MIT-licensed speech recognition (optional)

### macOS / Linux

For macOS and Linux, binaries can be installed via:

```bash
# macOS
brew install ffmpeg yt-dlp

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg
wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O resources/yt-dlp
chmod +x resources/yt-dlp

# Or use the setup script
./setup-binaries.sh
```

## 🎨 Available Effects

| Effect | Description | Best For |
|--------|-------------|----------|
| **Typewriter** | Text appears character by character | Dramatic reveals |
| **Bounce** | Letters drop and bounce into place | Energetic content |
| **Wave** | Text ripples in sine wave pattern | Music videos |
| **Rainbow** | Cycles through color spectrum | Fun, vibrant content |
| **Glitch** | Digital corruption with RGB splits | Tech/gaming content |
| **Sparkle** | Magical particles around text | Special moments |
| **Neon** | Glowing neon sign effect | Night scenes |
| **Glow** | Soft ethereal glow | Atmospheric content |
| **Fade** | Smooth fade in/out | Professional transitions |
| **Shake** | Dynamic text trembling | Action scenes |

## 🛠️ Development

### Project Structure
```
autogif/
├── autogif/              # Main application code
│   ├── effects/          # Visual effects plugins
│   │   └── plugins/      # Individual effect implementations
│   ├── fonts/            # Bundled fonts
│   ├── config.py         # Configuration
│   ├── main.py           # Gradio UI
│   └── processing.py     # Core video/GIF processing
├── resources/            # Platform binaries
├── build.bat/sh          # Build scripts
├── run.bat/sh            # Run scripts
└── requirements.txt      # Python dependencies
```

### Creating Custom Effects

1. Create a new file in `autogif/effects/plugins/`
2. Inherit from `EffectBase`
3. Implement required methods:

```python
from autogif.effects.effect_base import EffectBase

class MyEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "my-effect"
    
    @property
    def display_name(self) -> str:
        return "My Effect"
    
    def transform(self, frame_image, text, **kwargs):
        # Your effect logic here
        return modified_frame
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-effect`)
3. Commit your changes (`git commit -m 'Add amazing effect'`)
4. Push to the branch (`git push origin feature/amazing-effect`)
5. Open a Pull Request

## 📝 License & Credits

### AutoGIF License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Components

AutoGIF includes or uses the following third-party components:

#### Included Binaries (Windows)

| Component | License | Source |
|-----------|---------|---------|
| **FFmpeg** | LGPL v2.1+ | [ffmpeg.org](https://ffmpeg.org/) |
| **yt-dlp** | Unlicense | [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| **Whisper** | MIT | [github.com/Const-me/Whisper](https://github.com/Const-me/Whisper) |

#### Included Fonts

| Font | License | Copyright |
|------|---------|-----------|
| **JetBrains Mono** | OFL 1.1 | © JetBrains s.r.o. |
| **Fira Code** | OFL 1.1 | © The Fira Code Project Authors |
| **IBM VGA** | CC BY-SA 4.0 | © VileR |
| **Consolas** | Proprietary* | © Microsoft Corporation |
| **Impact** | Proprietary* | © Microsoft Corporation |

*Note: Consolas and Impact are included for compatibility. Users should ensure they have appropriate licenses for these fonts.

#### Python Dependencies

Major Python packages used:
- **Gradio** (Apache 2.0) - Web interface
- **Pillow** (HPND) - Image processing
- **OpenCV** (Apache 2.0) - Video processing
- **faster-whisper** (MIT) - Speech recognition
- **NumPy** (BSD) - Numerical computing

### Binary Distribution Notice

This software includes pre-compiled binaries for convenience. These binaries are distributed under their respective licenses:

- FFmpeg binaries are compiled from source available at [ffmpeg.org](https://ffmpeg.org/) and are licensed under LGPL v2.1 or later. Source code is available at the FFmpeg website.
- yt-dlp is distributed under the Unlicense (public domain).
- Users are responsible for complying with all applicable licenses when using this software.

### Acknowledgments

Special thanks to:
- The FFmpeg team for their powerful multimedia framework
- The yt-dlp community for maintaining an excellent YouTube downloader
- OpenAI for the Whisper speech recognition model
- The Gradio team for their intuitive web UI framework
- All font creators who made their work available under open licenses

## 🙏 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/autogif/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/autogif/discussions)

---

Made with 💚 in the Matrix 
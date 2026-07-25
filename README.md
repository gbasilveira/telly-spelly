# Telly Spelly for KDE Plasma

A sleek KDE Plasma application that records audio and transcribes it in real-time using OpenAI's Whisper. Created by Guilherme da Silveira.

## Features

- 🎙️ **Easy Recording**: Start/stop recording with a single click in the system tray
- 🔊 **Live Volume Meter**: Visual feedback while recording
- ⚡ **Global Shortcuts**: Configurable keyboard shortcuts for quick recording
- 🎯 **Microphone Selection**: Choose your preferred input device
- 📋 **Instant Clipboard**: Transcribed text is automatically copied to your clipboard
- 🎨 **Native KDE Integration**: Follows your system theme and integrates seamlessly with Plasma

## Installation

1. Ensure all [Prerequisites](#prerequisites) are installed first.

2. Clone the repository:
```bash
git clone https://github.com/gbasilveira/telly-spelly.git
cd telly-spelly
```

3. Run the installer:
```bash
python3 install.py
```

The installer uses [uv](https://astral.sh/uv) to:
- Build a locked virtual environment from `uv.lock` (pinned Python + dependencies, including `torch` and `openai-whisper`)
- Wire the app into `~/.local` (launcher, desktop entry, icon)

Because uv manages its own Python interpreter and all dependencies are
pinned in `uv.lock`, the install is insulated from system Python upgrades.

## Prerequisites

### System Requirements
- [uv](https://astral.sh/uv) (manages Python + dependencies)
- KDE Plasma desktop environment
- PortAudio (for audio recording)
- CUDA-capable GPU (optional, for faster transcription)

### 1. uv

Install uv (see https://docs.astral.sh/uv/getting-started/installation/):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. System Packages

pyaudio builds against PortAudio:

**Ubuntu/Debian:**
```bash
sudo apt install portaudio19-dev
```

**Fedora:**
```bash
sudo dnf install portaudio-devel
```

### 3. GPU Acceleration (Optional but Recommended)

For significantly faster transcription, install NVIDIA drivers:
```bash
sudo apt install nvidia-driver-580-open
sudo reboot
```

Verify the GPU is visible:
```bash
nvidia-smi
```

torch is installed automatically **with CUDA support** by `uv sync` — the
PyTorch CUDA wheel index is configured in `pyproject.toml`. After
installing, verify CUDA is available:
```bash
.venv/bin/python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

Without a GPU, Whisper runs on CPU (slower but functional).

### 4. Global Shortcuts (Input Group)

Global keyboard shortcuts use `evdev` to capture key events, which requires read access to `/dev/input/event*` devices. Add your user to the `input` group:

```bash
sudo usermod -aG input $USER
```

**Log out and back in** for the group change to take effect.

Verify with:
```bash
groups | grep input
```

> **Note:** Without this, the app will still work but global shortcuts won't function (you'll need to click the tray icon instead).

## Usage

1. Launch "Telly Spelly" from your application menu or run:
```bash
telly-spelly
```

2. Click the tray icon or use configured shortcuts to start/stop recording
3. When recording stops, the audio will be automatically transcribed
4. The transcribed text is copied to your clipboard

## Configuration

- Right-click the tray icon and select "Settings"
- Configure:
  - Input device selection
  - Global keyboard shortcuts
  - Whisper model selection
  - Interface preferences

## Uninstallation

To remove the application:
```bash
python3 uninstall.py
```

## Technical Details

- Built with PyQt6 for the GUI
- Uses OpenAI's Whisper for transcription
- Integrates with KDE Plasma using system tray and global shortcuts
- Records audio using PyAudio
- Processes audio with scipy for optimal quality

## Contributing

Contributions are welcome! Feel free to:
- Report issues
- Suggest features
- Submit pull requests

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the amazing speech recognition model
- KDE Community for the excellent desktop environment
- All contributors and users of this project

## Author

**Guilherme da Silveira**

---

Made with ❤️ for the KDE Community

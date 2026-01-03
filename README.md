# Telly Spelly

Voice-to-text transcription using OpenAI's Whisper.

Press a keyboard shortcut, speak, press again - your words are transcribed and copied to the clipboard.

**Supports:** KDE Plasma 5/6 and XFCE4

## Installation

### 1. Install system dependencies

**Ubuntu/Debian:**
```bash
sudo apt install portaudio19-dev libdbus-1-dev python3-dev python3-venv
```

**Arch Linux:**
```bash
sudo pacman -S portaudio dbus python
```

### 2. Install Telly Spelly

**With uv (recommended):**
```bash
uv tool install telly-spelly --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/
```

**With pip:**
```bash
pip install telly-spelly --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/
```

### 3. Run

```bash
telly-spelly
```

On first launch, desktop integration is set up automatically:
- Application menu entry
- System tray icon
- Keyboard shortcut (Ctrl+Alt+R)

> **Note:** The app automatically detects your desktop environment (KDE or XFCE4) and configures itself appropriately.

## Usage

1. Press `Ctrl+Alt+R` or click the tray icon
2. Speak - a recording indicator appears
3. Press `Ctrl+Alt+R` again to stop
4. Text is copied to your clipboard

## Configuration

Right-click the tray icon → **Settings**:
- Whisper model (tiny, base, small, medium, large, turbo)
- Language
- Input device

## Requirements

- **Desktop:** KDE Plasma 5/6 or XFCE4
- **Python:** 3.9 or newer
- **Storage:** ~8GB (7GB for PyTorch/CUDA, 1GB for Whisper models)
- **GPU:** NVIDIA recommended (CPU also works, but uses less disk space without CUDA)

## Troubleshooting

**Shortcuts not working?**

Try these steps:
1. Log out and back in after first installation
2. Check your desktop's keyboard shortcuts settings:
   - **KDE:** System Settings → Shortcuts → Telly Spelly
   - **XFCE4:** Settings → Keyboard → Application Shortcuts
3. Look for Ctrl+Alt+R assigned to Telly Spelly

**No audio captured?**
- Verify your microphone works in system settings
- Try selecting a different input device in Telly Spelly settings (right-click tray icon → Settings)

**Slow transcription?**
- Use a smaller Whisper model (tiny or base) in Settings
- For faster performance, install CUDA for GPU acceleration

## License

MIT License

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper)
- Original concept by Guilherme da Silveira

# CameraBlur

Linux virtual camera with AI-powered background blur and replacement. Creates a virtual webcam that other applications (Zoom, Teams, OBS, etc.) can use as a video source.

## Features

- **Real-time background blur** with adjustable intensity
- **Background replacement** with images or videos
- **Dual segmentation backends**:
  - RVM (GPU-accelerated via PyTorch) - ~30 FPS at 1080p
  - MediaPipe (CPU-based) - for systems without GPU
- **Interactive TUI** for real-time control
- **Configuration file support** with hot-reload in TUI

## Demo

### GPU Version Performance

The following video demonstrates the accuracy and performance of the background blur effect using the RVM (GPU-accelerated) backend:

<video src="video_example.mp4" width="100%" controls></video>

This example shows real-time background segmentation and blur at approximately 30 FPS at 1080p resolution using an NVIDIA GPU.

## Requirements

- Linux with v4l2loopback kernel module
- Python 3.11-3.13
- Physical webcam
- NVIDIA GPU (optional, for RVM backend)

## Installation

```bash
# Install v4l2loopback (Arch Linux)
sudo pacman -S v4l2loopback-dkms

# Install v4l2loopback (Ubuntu/Debian)
sudo apt install v4l2loopback-dkms

# Load the kernel module
sudo modprobe v4l2loopback devices=1 card_label='VirtualCam'

# Clone and install
git clone https://github.com/youruser/camerablur.git
cd camerablur
uv sync
```

## Quick Start

```bash
# Check system requirements
camerablur check

# List available cameras
camerablur list-devices

# Start with default settings (GPU blur)
camerablur run

# Start with CPU backend
camerablur run --no-gpu

# Start with background image
camerablur run --background ~/wallpaper.jpg

# Launch interactive TUI
camerablur tui
```

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `camerablur run` | Start virtual camera |
| `camerablur tui` | Launch interactive TUI |
| `camerablur list-devices` | Show available cameras |
| `camerablur check` | Verify system requirements |

### Run Options

```bash
camerablur run [OPTIONS]

Options:
  -c, --config PATH       Configuration file path
  -d, --camera INT        Camera device ID
  -b, --blur INT          Blur intensity (odd number)
  -bg, --background PATH  Background image or video
  -p, --preview           Show preview window
  --gpu / --no-gpu        Enable/disable GPU acceleration
  -m, --model TEXT        RVM model: mobilenetv3 (fast) or resnet50 (quality)
```

### Examples

```bash
# Use camera 2 with blur intensity 51
camerablur run --camera 2 --blur 51

# Replace background with video, show preview
camerablur run --background ~/beach.mp4 --preview

# Use high-quality RVM model
camerablur run --gpu --model resnet50
```

## TUI Controls

Launch with `camerablur tui`:

| Key | Action |
|-----|--------|
| `s` | Start pipeline |
| `x` | Stop pipeline |
| `q` | Quit |
| `p` | Toggle preview window |
| `Ctrl+S` | Save configuration |

The TUI provides real-time sliders for blur intensity and feather amount, camera selection, effect mode switching, and FPS display.

## Configuration

Create `config.yaml` in the current directory or `~/.config/camerablur/config.yaml`:

```yaml
camera:
  device_id: 0
  width: 1280
  height: 720
  fps: 30

segmentation:
  backend: rvm              # rvm (GPU) or mediapipe (CPU)
  rvm_model: mobilenetv3    # mobilenetv3 or resnet50
  threshold: 0.5

effect:
  mode: blur                # blur, image, video, none
  blur_intensity: 101       # Must be odd
  feather_amount: 3
  background_path: null

output:
  device: null              # Auto-detect virtual camera

debug:
  preview_window: false
```

## Troubleshooting

### No virtual camera found

```bash
# Load v4l2loopback module
sudo modprobe v4l2loopback devices=1 card_label='VirtualCam'

# Make persistent (create file):
# /etc/modules-load.d/v4l2loopback.conf
v4l2loopback
```

### Camera not detected

```bash
# List all video devices
camerablur list-devices

# Check device permissions
ls -la /dev/video*
sudo usermod -aG video $USER  # Then log out/in
```

### Low FPS

- Use `mobilenetv3` model instead of `resnet50`
- Lower resolution in config (e.g., 640x480)
- Use `--no-gpu` if GPU is slow/unavailable
- Reduce `blur_intensity` value

## Supported Formats

**Background images**: JPG, PNG, WebP, BMP, TIFF

**Background videos**: MP4, WebM, AVI, MKV, MOV

## License

MIT

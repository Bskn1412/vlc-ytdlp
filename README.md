# 🎬 Smart YTVLC Player

A terminal-based YouTube player using **yt-dlp** for stream extraction and **VLC** for playback.

## ✨ Features

* 🎥 Single YouTube video playback
* 📋 YouTube playlist support
* 🔀 YouTube Mix support
* 🎵 Audio-only mode
* 🎬 Video mode with format selection
* ⚡ Direct streaming to VLC
* ⏭️ Next / Previous controls
* 🔁 Mix looping
* 🐧 Fedora/Linux support
* 🐍 Python 3.12 support

## 🛠️ Requirements

* Fedora/Linux
* Python **3.12.x**
* VLC
* FFmpeg
* yt-dlp

### Install VLC

```bash
sudo dnf install vlc
```

### Check FFmpeg

```bash
ffmpeg -version
```

### Install yt-dlp

```bash
python -m pip install -U yt-dlp
```

## 🚀 Setup & Run

Clone/download the project and enter the directory:

```bash
cd vlc-ytdlp-main
```

Create a Python 3.12 virtual environment:

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install yt-dlp:

```bash
python -m pip install -U yt-dlp
```

Run the player:

```bash
python player.py
```

> Replace `player.py` with your actual Python filename.

## 🎮 Controls

| Key      | Action   |
| -------- | -------- |
| `N`      | Next     |
| `P`      | Previous |
| `Q`      | Quit     |
| `Ctrl+C` | Stop     |

## ▶️ Usage

1. Run the player.
2. Enter a YouTube video, playlist, or Mix URL.
3. Select:

   * `1` → Audio
   * `2` → Video
4. For video mode, select a format or press **Enter** for best available.
5. VLC starts playback automatically.

## 🔄 Playback Flow

```text
YouTube
   ↓
yt-dlp
   ↓
Extract stream
   ↓
Python Player
   ↓
VLC
   ↓
Playback
```

## ⚠️ Note

Keep **yt-dlp updated** because YouTube's streaming system can change:

```bash
python -m pip install -U yt-dlp
```

For normal playback, the project streams media directly rather than downloading the complete file first.

## Happy Streaming...

import os
import subprocess
import time
import yt_dlp
import msvcrt


# ================= PATHS =================
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
FFMPEG_PATH = "ffmpeg"  # must be in PATH

# ================= CONFIG =================
YDL_BASE = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
}
YTDLP_RETRIES = 10
YTDLP_FRAGMENT_RETRIES = 10

# ================= HELPERS =================
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_info(url, flat=False):
    opts = YDL_BASE.copy()
    if flat:
        opts.update({'extract_flat': True})
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def is_playlist(info):
    return info and isinstance(info.get("entries"), list)

def detect_type(url, info):
    if "list=RD" in url:
        return "mix"
    if is_playlist(info):
        return "playlist"
    return "single"

def build_playlist(info):
    out = []
    for e in info.get("entries", []):
        if e:
            out.append({
                "title": e.get("title", "Unknown"),
                "url": e.get("url") or e.get("webpage_url")
            })
    return out

# ================= FORMAT DISPLAY =================
def show_formats(info):
    print("\n🎬 Formats:\n")
    for f in info.get("formats", []):
        if f.get("vcodec") != "none":
            fid = f.get("format_id")
            res = f.get("height")
            fps = f.get("fps", "")
            audio = f.get("acodec") != "none"
            tag = "" if audio else " (no audio)"
            print(f"{fid} → {res}p {fps}{tag}")

# ================= STREAM EXTRACTION =================
def extract_streams(url, mode, fmt=None):
    print("\n[DEBUG] Extracting streams...")

    ydl_opts = YDL_BASE.copy()

    if mode == "audio":
        ydl_opts["format"] = "bestaudio/best"
    else:
        if fmt:
            ydl_opts["format"] = f"{fmt}+bestaudio/best"
        else:
            ydl_opts["format"] = "bestvideo+bestaudio/best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "Unknown")

    # direct
    if info.get("url"):
        print("[DEBUG] Direct stream")
        return [info["url"]], title

    # DASH
    if info.get("requested_formats"):
        print("[DEBUG] DASH streams detected")

        streams = []
        for f in info["requested_formats"]:
            kind = "video" if f.get("vcodec") != "none" else "audio"
            print(f"[DEBUG] {kind}: {f.get('format_id')}")
            streams.append(f["url"])

        return streams, title

    print("[ERROR] No streams found")
    return None, title

# ================= PIPE MERGE =================
def play_with_vlc_dual(video_url, audio_url):
    cmd = [
        VLC_PATH,
        video_url,
        f":input-slave={audio_url}",
        "--network-caching=3000",
        "--file-caching=3000",
        "--live-caching=3000",
        "--no-video-title-show"
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ================= PLAYER =================
class Player:
    def __init__(self, playlist, mode, type_):
        self.playlist = playlist
        self.mode = mode
        self.type = type_
        self.index = 0
        self.process = None
        self.ytdlp_process = None

    def stop(self):
        if self.ytdlp_process and self.ytdlp_process.poll() is None:
            self.ytdlp_process.kill()
        os.system("taskkill /f /im vlc.exe >nul 2>&1")

    def play_stream(self, streams, title, url):
        self.stop()

        # ✅ if single stream → normal
        if len(streams) == 1:
            print("[DEBUG] Playing direct stream")

            cmd = [
                VLC_PATH,
                streams[0],
                "--network-caching=2000",
                "--no-video-title-show",
                "--play-and-exit"
            ]

            self.ytdlp_process = None
            self.process = subprocess.Popen(cmd)

        else:
            # ❌ DASH → use pipe fix
            video_url = streams[0]
            audio_url = streams[1]

            self.ytdlp_process = None
            self.process = play_with_vlc_dual(video_url, audio_url)

        clear()
        print(f"🎵 Now Playing ({self.index+1}/{len(self.playlist)})")
        print(f"▶ {title}")
        print("\nControls: N (Next) / P (Previous) / Q (Quit)")

    def play_current(self):
        track = self.playlist[self.index]

        print(f"\nLoading: {track['title']}")

        try:
            info = get_info(track["url"])

            fmt = None
            if self.mode == "video":
                show_formats(info)
                fmt = input("\nFormat (ENTER=best): ").strip() or None

            streams, title = extract_streams(track["url"], self.mode, fmt)

            if not streams:
                print("❌ Failed, skipping...")
                self.next()
                return

            print("[DEBUG] Stream count:", len(streams))

            self.play_stream(streams, title, track["url"])

        except Exception as e:
            print("Error:", e)
            self.next()

    def next(self):
        self.index += 1
        if self.index >= len(self.playlist):
            if self.type == "mix":
                self.index = 0
            else:
                return
        self.play_current()

    def prev(self):
        self.index = (self.index - 1) % len(self.playlist)
        self.play_current()

    def run(self):
        self.play_current()

        while True:
            # Only checks console window input (not global hotkeys)
            if msvcrt.kbhit():
                key = msvcrt.getch().decode().lower()
                
                if key == "n":
                    self.next()
                    time.sleep(0.3)
                elif key == "p":
                    self.prev()
                    time.sleep(0.3)
                elif key == "q":
                    self.stop()
                    break

            if self.ytdlp_process and self.ytdlp_process.poll() is not None:
                if self.process and self.process.poll() is None:
                    print("[ERROR] yt-dlp failed during pipe merge.")
                    self.process.terminate()
                time.sleep(1)
                self.next()
                continue

            if self.process and self.process.poll() is not None:
                time.sleep(2)
                self.next()

            time.sleep(0.1)

# ================= MAIN =================
clear()
print("SMART YTVLC PLAYER")
print("==================================\n")

url = input("Enter URL: ").strip()

info = get_info(url, flat=True)
type_ = detect_type(url, info)

if type_ == "playlist":
    playlist = build_playlist(info)
elif type_ == "mix":
    playlist = build_playlist(info)
else:
    full = get_info(url)
    playlist = [{"title": full.get("title"), "url": url}]

mode = "audio" if input("[1] Audio [2] Video > ") == "1" else "video"

player = Player(playlist, mode, type_)
player.run()
 
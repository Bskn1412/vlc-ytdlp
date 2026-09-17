import os
import sys
import subprocess
import time
import select
import termios
import tty

import yt_dlp


# ============================================================
# PATHS
# ============================================================

# Fedora: VLC and FFmpeg should be available in PATH
VLC_PATH = "vlc"
FFMPEG_PATH = "ffmpeg"


# ============================================================
# CONFIG
# ============================================================

YDL_BASE = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}

YTDLP_RETRIES = 10
YTDLP_FRAGMENT_RETRIES = 10


# ============================================================
# TERMINAL HELPERS
# ============================================================

def clear():
    os.system("clear")


def get_key():
    """
    Non-blocking keyboard input for Linux terminal.
    Returns the pressed key or None.
    """

    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1).lower()

    return None


# ============================================================
# YT-DLP HELPERS
# ============================================================

def get_info(url, flat=False):

    opts = YDL_BASE.copy()

    if flat:
        opts.update({
            "extract_flat": True
        })

    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(
            url,
            download=False
        )


def is_playlist(info):

    return (
        info
        and isinstance(info.get("entries"), list)
    )


def detect_type(url, info):

    if "list=RD" in url:
        return "mix"

    if is_playlist(info):
        return "playlist"

    return "single"


def build_playlist(info):

    out = []

    for entry in info.get("entries", []):

        if not entry:
            continue

        out.append({
            "title": entry.get(
                "title",
                "Unknown"
            ),

            "url": (
                entry.get("url")
                or entry.get("webpage_url")
            )
        })

    return out


# ============================================================
# FORMAT DISPLAY
# ============================================================

def show_formats(info):

    print("\n🎬 Formats:\n")

    for fmt in info.get("formats", []):

        if fmt.get("vcodec") == "none":
            continue

        format_id = fmt.get(
            "format_id",
            "?"
        )

        resolution = fmt.get(
            "height",
            "?"
        )

        fps = fmt.get(
            "fps",
            ""
        )

        has_audio = (
            fmt.get("acodec") != "none"
        )

        audio_tag = (
            ""
            if has_audio
            else " (no audio)"
        )

        print(
            f"{format_id} → "
            f"{resolution}p "
            f"{fps}"
            f"{audio_tag}"
        )


# ============================================================
# STREAM EXTRACTION
# ============================================================

def extract_streams(url, mode, fmt=None):

    print("\n[DEBUG] Extracting streams...")

    ydl_opts = YDL_BASE.copy()

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    if mode == "audio":

        ydl_opts["format"] = (
            "bestaudio/best"
        )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    else:

        if fmt:

            ydl_opts["format"] = (
                f"{fmt}+bestaudio/best"
            )

        else:

            ydl_opts["format"] = (
                "bestvideo+bestaudio/best"
            )

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

    title = info.get(
        "title",
        "Unknown"
    )

    # --------------------------------------------------------
    # Single direct stream
    # --------------------------------------------------------

    if info.get("url"):

        print(
            "[DEBUG] Direct stream"
        )

        return [
            info["url"]
        ], title

    # --------------------------------------------------------
    # DASH / separate streams
    # --------------------------------------------------------

    if info.get("requested_formats"):

        print(
            "[DEBUG] DASH streams detected"
        )

        streams = []

        for fmt_info in info[
            "requested_formats"
        ]:

            kind = (
                "video"
                if fmt_info.get("vcodec") != "none"
                else "audio"
            )

            print(
                f"[DEBUG] {kind}: "
                f"{fmt_info.get('format_id')}"
            )

            if fmt_info.get("url"):

                streams.append(
                    fmt_info["url"]
                )

        return streams, title

    # --------------------------------------------------------
    # Nothing found
    # --------------------------------------------------------

    print(
        "[ERROR] No streams found"
    )

    return None, title


# ============================================================
# VLC DUAL STREAM
# ============================================================

def play_with_vlc_dual(
    video_url,
    audio_url
):

    cmd = [
        VLC_PATH,

        video_url,

        f"--input-slave={audio_url}",

        "--network-caching=3000",

        "--file-caching=3000",

        "--live-caching=3000",

        "--no-video-title-show",

        "--play-and-exit",
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# ============================================================
# PLAYER
# ============================================================

class Player:

    def __init__(
        self,
        playlist,
        mode,
        type_
    ):

        self.playlist = playlist

        self.mode = mode

        self.type = type_

        self.index = 0

        self.process = None

        self.ytdlp_process = None

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    def stop(self):

        # Stop yt-dlp process if one exists
        if (
            self.ytdlp_process
            and self.ytdlp_process.poll() is None
        ):

            self.ytdlp_process.terminate()

            try:
                self.ytdlp_process.wait(
                    timeout=2
                )

            except subprocess.TimeoutExpired:

                self.ytdlp_process.kill()

        # Stop VLC process
        if (
            self.process
            and self.process.poll() is None
        ):

            self.process.terminate()

            try:
                self.process.wait(
                    timeout=2
                )

            except subprocess.TimeoutExpired:

                self.process.kill()

        self.process = None
        self.ytdlp_process = None

    # --------------------------------------------------------
    # PLAY STREAM
    # --------------------------------------------------------

    def play_stream(
        self,
        streams,
        title,
        url
    ):

        self.stop()

        # ----------------------------------------------------
        # Single stream
        # ----------------------------------------------------

        if len(streams) == 1:

            print(
                "[DEBUG] Playing direct stream"
            )

            cmd = [

                VLC_PATH,

                streams[0],

                "--network-caching=2000",

                "--no-video-title-show",

                "--play-and-exit",
            ]

            self.process = subprocess.Popen(
                cmd
            )

        # ----------------------------------------------------
        # Video + Audio
        # ----------------------------------------------------

        else:

            print(
                "[DEBUG] Playing video + audio streams"
            )

            video_url = streams[0]

            audio_url = streams[1]

            self.process = (
                play_with_vlc_dual(
                    video_url,
                    audio_url
                )
            )

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        clear()

        print(
            f"🎵 Now Playing "
            f"({self.index + 1}/"
            f"{len(self.playlist)})"
        )

        print()

        print(
            f"▶ {title}"
        )

        print()

        print(
            "Controls:"
        )

        print(
            "  N → Next"
        )

        print(
            "  P → Previous"
        )

        print(
            "  Q → Quit"
        )

    # --------------------------------------------------------
    # PLAY CURRENT
    # --------------------------------------------------------

    def play_current(self):

        track = self.playlist[
            self.index
        ]

        print(
            f"\nLoading: "
            f"{track['title']}"
        )

        try:

            # ----------------------------------------------
            # Get information
            # ----------------------------------------------

            info = get_info(
                track["url"]
            )

            fmt = None

            # ----------------------------------------------
            # Video format selection
            # ----------------------------------------------

            if self.mode == "video":

                show_formats(info)

                fmt = input(
                    "\nFormat "
                    "(ENTER=best): "
                ).strip()

                if not fmt:
                    fmt = None

            # ----------------------------------------------
            # Extract streams
            # ----------------------------------------------

            streams, title = (
                extract_streams(
                    track["url"],
                    self.mode,
                    fmt
                )
            )

            # ----------------------------------------------
            # Failed
            # ----------------------------------------------

            if not streams:

                print(
                    "❌ Failed, skipping..."
                )

                time.sleep(1)

                self.next()

                return

            print(
                "[DEBUG] Stream count:",
                len(streams)
            )

            # ----------------------------------------------
            # Play
            # ----------------------------------------------

            self.play_stream(
                streams,
                title,
                track["url"]
            )

        except Exception as e:

            print(
                "\n❌ Error:",
                e
            )

            time.sleep(1)

            self.next()

    # --------------------------------------------------------
    # NEXT
    # --------------------------------------------------------

    def next(self):

        self.index += 1

        # End of playlist
        if self.index >= len(
            self.playlist
        ):

            # Mix → loop
            if self.type == "mix":

                self.index = 0

            # Normal playlist → stop
            else:

                self.stop()

                print(
                    "\nPlaylist finished."
                )

                return

        self.play_current()

    # --------------------------------------------------------
    # PREVIOUS
    # --------------------------------------------------------

    def prev(self):

        self.index = (
            self.index - 1
        ) % len(self.playlist)

        self.play_current()

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    def run(self):

        # Save terminal settings
        old_settings = (
            termios.tcgetattr(
                sys.stdin
            )
        )

        try:

            # Enable single-character input
            tty.setcbreak(
                sys.stdin.fileno()
            )

            self.play_current()

            while True:

                # ------------------------------------------
                # Keyboard
                # ------------------------------------------

                key = get_key()

                if key == "n":

                    self.next()

                    time.sleep(0.3)

                elif key == "p":

                    self.prev()

                    time.sleep(0.3)

                elif key == "q":

                    self.stop()

                    break

                # ------------------------------------------
                # yt-dlp process
                # ------------------------------------------

                if (
                    self.ytdlp_process
                    and self.ytdlp_process.poll()
                    is not None
                ):

                    if (
                        self.process
                        and self.process.poll()
                        is None
                    ):

                        print(
                            "[ERROR] "
                            "yt-dlp failed "
                            "during pipe merge."
                        )

                        self.process.terminate()

                    time.sleep(1)

                    self.next()

                    continue

                # ------------------------------------------
                # VLC finished
                # ------------------------------------------

                if (
                    self.process
                    and self.process.poll()
                    is not None
                ):

                    time.sleep(2)

                    self.next()

                # ------------------------------------------
                # Prevent CPU spinning
                # ------------------------------------------

                time.sleep(0.1)

        except KeyboardInterrupt:

            print(
                "\n\nStopping..."
            )

            self.stop()

        finally:

            # ALWAYS restore terminal
            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                old_settings
            )


# ============================================================
# MAIN
# ============================================================

def main():

    clear()

    print(
        "SMART YTVLC PLAYER FOR LINUX\n"
    )

    print(
        "==================================\n"
    )

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    url = input(
        "Enter URL: "
    ).strip()

    if not url:

        print(
            "❌ URL cannot be empty."
        )

        return

    # --------------------------------------------------------
    # Detect type
    # --------------------------------------------------------

    try:

        info = get_info(
            url,
            flat=True
        )

    except Exception as e:

        print(
            "\n❌ Could not extract URL:"
        )

        print(e)

        return

    type_ = detect_type(
        url,
        info
    )

    # --------------------------------------------------------
    # Playlist
    # --------------------------------------------------------

    if type_ == "playlist":

        playlist = build_playlist(
            info
        )

    # --------------------------------------------------------
    # YouTube Mix
    # --------------------------------------------------------

    elif type_ == "mix":

        playlist = build_playlist(
            info
        )

    # --------------------------------------------------------
    # Single video
    # --------------------------------------------------------

    else:

        try:

            full = get_info(
                url
            )

            playlist = [
                {
                    "title": full.get(
                        "title",
                        "Unknown"
                    ),

                    "url": url
                }
            ]

        except Exception as e:

            print(
                "\n❌ Could not load video:"
            )

            print(e)

            return

    # --------------------------------------------------------
    # Empty playlist check
    # --------------------------------------------------------

    if not playlist:

        print(
            "\n❌ No videos found."
        )

        return

    # --------------------------------------------------------
    # Mode
    # --------------------------------------------------------

    choice = input(
        "\n[1] Audio "
        "[2] Video > "
    ).strip()

    if choice == "1":

        mode = "audio"

    else:

        mode = "video"

    # --------------------------------------------------------
    # Start player
    # --------------------------------------------------------

    player = Player(
        playlist,
        mode,
        type_
    )

    player.run()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
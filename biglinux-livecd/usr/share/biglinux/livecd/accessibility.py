"""Accessibility utilities — speech via Kokoro TTS (koko CLI)."""

import os
import subprocess
import tempfile
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from logging_config import get_logger

logger = get_logger()

_HAS_ANNOUNCE = hasattr(Gtk.Accessible, "announce")

# ── Kokoro TTS paths ────────────────────────────────────────
_KOKO_BIN = "/usr/bin/koko"
_KOKO_MODEL = "/usr/share/biglinux-kokoro-tts/model/model.onnx"
_KOKO_VOICES = "/usr/share/biglinux-kokoro-tts/voices/voices.bin"

# ── Global accessibility state ──────────────────────────────
_accessibility_enabled = False
_speak_gen = 0
_speak_lock = threading.Lock()
_play_process = None

# Voice configuration set by the language screen selection
_current_voice = "af_heart"
_current_lang_code = "en-us"


def is_accessibility_enabled() -> bool:
    return _accessibility_enabled


def set_accessibility_enabled(enabled: bool) -> None:
    global _accessibility_enabled
    _accessibility_enabled = enabled
    logger.info(f"Accessibility {'enabled' if enabled else 'disabled'}")


def set_speak_voice(voice: str, lang_code: str) -> None:
    """Set the voice and language for speak() calls (called when user selects a language)."""
    global _current_voice, _current_lang_code
    _current_voice = voice
    _current_lang_code = lang_code


def speak(text: str) -> None:
    """Speak text using koko directly. Non-blocking, cancels previous speech."""
    if not _accessibility_enabled or not text:
        return
    logger.info(
        f"speak() called: '{text}' voice={_current_voice} lang={_current_lang_code}"
    )
    stop_speaking()
    global _speak_gen
    with _speak_lock:
        _speak_gen += 1
        gen = _speak_gen

    def _do_speak():
        global _play_process
        tmpwav = None
        try:
            fd, tmpwav = tempfile.mkstemp(prefix="a11y-", suffix=".wav")
            os.close(fd)
            cmd = [
                _KOKO_BIN,
                "-m",
                _KOKO_MODEL,
                "-d",
                _KOKO_VOICES,
                "-l",
                _current_lang_code,
                "-s",
                _current_voice,
                "--force-style",
                "true",
                "--speed",
                "1.5",
                "text",
                text,
                "-o",
                tmpwav,
            ]
            logger.info(f"speak() running koko: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
            )
            if proc.returncode != 0:
                logger.info(
                    f"speak() koko failed rc={proc.returncode} stderr={proc.stderr.decode()[:200]}"
                )
                return
            with _speak_lock:
                if gen != _speak_gen:
                    logger.info("speak() discarded (gen changed)")
                    return
            fsize = os.path.getsize(tmpwav) if os.path.isfile(tmpwav) else 0
            logger.info(f"speak() WAV generated: {tmpwav} size={fsize}")
            if fsize > 0:
                play = subprocess.Popen(
                    ["paplay", tmpwav],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                with _speak_lock:
                    _play_process = play
                play.wait(timeout=15)
                if play.returncode != 0:
                    logger.info(
                        f"speak() paplay failed rc={play.returncode} stderr={play.stderr.read().decode()[:200]}"
                    )
                else:
                    logger.info("speak() playback complete")
        except Exception as e:
            logger.info(f"speak() exception: {e}")
        finally:
            if tmpwav and os.path.isfile(tmpwav):
                try:
                    os.unlink(tmpwav)
                except OSError:
                    pass

    threading.Thread(target=_do_speak, daemon=True).start()


def stop_speaking() -> None:
    """Cancel any ongoing speech playback."""
    global _speak_gen, _play_process
    with _speak_lock:
        _speak_gen += 1
        if _play_process and _play_process.poll() is None:
            _play_process.terminate()
        _play_process = None


def announce(widget: Gtk.Accessible, message: str, assertive: bool = False) -> None:
    """Announce a message to screen readers via AT-SPI2 only (no TTS speak)."""
    if not message or not widget:
        return
    if _HAS_ANNOUNCE:
        try:
            priority = (
                Gtk.AccessibleAnnouncementPriority.HIGH
                if assertive
                else Gtk.AccessibleAnnouncementPriority.MEDIUM
            )
            widget.announce(message, priority)
        except Exception as e:
            logger.debug(f"announce() failed: {e}")


def ensure_orca_disabled() -> None:
    """Kill any running ORCA and disable GNOME auto-start of screen reader."""
    subprocess.Popen(
        ["pkill", "-x", "orca"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.Popen(
        ["gsettings", "set", "org.gnome.desktop.a11y.applications",
         "screen-reader-enabled", "false"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    autostart_dir = os.path.expanduser("~/.config/autostart")
    override_file = os.path.join(autostart_dir, "orca-autostart.desktop")
    if not os.path.isfile(override_file):
        try:
            os.makedirs(autostart_dir, exist_ok=True)
            with open(override_file, "w") as f:
                f.write(
                    "[Desktop Entry]\nType=Application\nName=Orca Screen Reader\nHidden=true\n"
                )
        except OSError:
            pass
    logger.info("Ensured ORCA is disabled at startup")

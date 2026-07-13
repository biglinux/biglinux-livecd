from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

REPOSITORY = Path(__file__).resolve().parents[1]
LIVECD = REPOSITORY / "biglinux-livecd/usr/share/biglinux/livecd"
sys.path.insert(0, str(LIVECD))

from ui import language_view  # noqa: E402


def test_kokoro_cache_deduplicates_concurrent_generation(monkeypatch) -> None:
    cache_key = "test:voice"
    calls = 0

    def generate(command, **_kwargs):
        nonlocal calls
        calls += 1
        time.sleep(0.05)
        Path(command[command.index("-o") + 1]).write_bytes(b"wave")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(language_view.subprocess, "run", generate)
    threads = [
        threading.Thread(
            target=language_view.LanguageView._kokoro_generate,
            args=(None, "voice", "en", "hello", cache_key),
        )
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert calls == 1
    cached_path = language_view._KOKORO_WAV_CACHE.pop(cache_key)
    assert Path(cached_path).read_bytes() == b"wave"
    Path(cached_path).unlink()

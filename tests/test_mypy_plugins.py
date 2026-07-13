"""Type-check Calamares plugins in the same isolation used by its loader."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = (
    (ROOT / "biglinux-livecd/usr/lib/calamares/modules/btrfs/main.py", None),
    (ROOT / "biglinux-livecd/usr/lib/calamares/modules/btrfs-fix/main.py", None),
    (ROOT / "biglinux-livecd/usr/lib/calamares/modules/grubcfg-fix/main.py", None),
    (
        ROOT / "biglinux-livecd/usr/share/biglinux/livecd/main.py",
        ROOT / "biglinux-livecd/usr/share/biglinux/livecd",
    ),
    (
        ROOT / "biglinux-livecd/usr/share/biglinux/calamares/main.py",
        ROOT / "biglinux-livecd/usr/share/biglinux/calamares",
    ),
    (
        ROOT / "biglinux-livecd/usr/share/biglinux/calamares/gtk_dialog.py",
        ROOT / "biglinux-livecd/usr/share/biglinux/calamares",
    ),
)


def test_excluded_application_entrypoints_are_enumerated() -> None:
    roots = (
        ROOT / "biglinux-livecd/usr/share/biglinux/calamares",
        ROOT / "biglinux-livecd/usr/share/biglinux/livecd",
    )
    discovered = {
        path
        for source_root in roots
        for path in source_root.rglob("*.py")
        if (path.parent == source_root and path.name == "main.py")
        or path.stat().st_mode & 0o111
    }
    assert discovered <= {target for target, _mypy_path in TARGETS}


def test_applications_type_check_in_loader_isolation() -> None:
    mypy = shutil.which("mypy")
    assert mypy is not None, "mypy is required by the repository quality gate"

    for target, mypy_path in TARGETS:
        environment = os.environ.copy()
        if mypy_path is not None:
            environment["MYPYPATH"] = str(mypy_path)
        subprocess.run(
            [mypy, "--ignore-missing-imports", target],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )

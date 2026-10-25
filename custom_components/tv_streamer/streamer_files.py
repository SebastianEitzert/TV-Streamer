"""The streamer image (Dockerfile, server.py, …) ships with the integration and is served to the VM.

Integration and VM therefore always run matching versions: a new integration version changes the
manifest hash, the VM fetches the files and rebuilds its containers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

STREAMER_DIR = Path(__file__).parent / "streamer"
STREAMER_FILES = ("Dockerfile", "server.py", "client.html", "clock.html")


def load_streamer_files() -> dict[str, bytes]:
    """Read the files (blocking – run in the executor)."""
    return {name: (STREAMER_DIR / name).read_bytes() for name in STREAMER_FILES}


def files_manifest(files: dict[str, bytes]) -> str:
    """One line per file, `sha256  name`, in the format `sha256sum -c` understands."""
    return "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items())

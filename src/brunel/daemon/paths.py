import os
import stat
import tempfile
from pathlib import Path


def runtime_directory() -> Path:
    default = Path(tempfile.gettempdir()) / f"brunel-{os.getuid()}"
    path = Path(os.environ.get("BRUNEL_RUNTIME_DIR", str(default)))
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError(f"Runtime directory must be owned by the current user: {path}")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError(f"Runtime directory must have permissions 0700: {path}")
    return path


def socket_path() -> Path:
    return runtime_directory() / "daemon.sock"

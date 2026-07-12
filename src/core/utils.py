import os
import socket
from pathlib import Path
from typing import Optional

def get_free_port() -> int:
    """Gets a free TCP port in the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def find_session_file(workdir: Optional[str]) -> Optional[str]:
    """Finds a .session file in the given workdir and returns its path without the extension."""
    if not workdir:
        return None
    
    workdir_path = Path(workdir)
    search_paths = [
        workdir_path,
        workdir_path / "tdata",
        workdir_path / "tdata" / "user_data",
    ]

    for path in search_paths:
        if path.exists() and path.is_dir():
            try:
                # First, check for our standard "account.session"
                if (path / "account.session").is_file():
                    return str(path / "account")
                    
                # Otherwise, find the first .session file that is not a known telethon file
                for f in path.iterdir():
                    if f.is_file() and f.suffix == ".session" and "telethon" not in f.name:
                        return str(f.with_suffix(""))
            except OSError:
                continue
    return None

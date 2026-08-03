import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

class DockerTelegramManager:
    IMAGE_NAME = "shadowgram_telegram_embedded"

    @classmethod
    def is_image_built(cls) -> bool:
        try:
            res = subprocess.run(["docker", "image", "inspect", cls.IMAGE_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def build_image(cls) -> bool:
        dockerfile_dir = Path(__file__).resolve().parents[3] / "docker" / "telegram_embedded"
        if not dockerfile_dir.exists():
            return False
        try:
            cmd = ["docker", "build", "-t", cls.IMAGE_NAME, str(dockerfile_dir)]
            res = subprocess.run(cmd, check=True)
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def start_container(cls, workdir: str, proxy_url: Optional[str] = None, vnc_port: int = 6080) -> Optional[str]:
        workdir_abs = str(Path(workdir).resolve())
        container_name = f"shadowgram_tg_{Path(workdir).name}"
        
        # Stop existing if any
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{vnc_port}:6080",
            "-v", f"{workdir_abs}:/data",
            "-v", f"{workdir_abs}/tdata:/root/.local/share/TelegramDesktop/tdata",
            "-e", "WORKDIR_PATH=/data"
        ]
        
        if proxy_url:
            cmd.extend([
                "-e", f"HTTP_PROXY={proxy_url}",
                "-e", f"HTTPS_PROXY={proxy_url}",
                "-e", f"ALL_PROXY={proxy_url}",
                "-e", f"PROXY_URL={proxy_url}"
            ])
            
        cmd.append(cls.IMAGE_NAME)
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            container_id = res.stdout.strip()
            return container_id
        except Exception:
            return None

    @classmethod
    def stop_container(cls, workdir: str):
        container_name = f"shadowgram_tg_{Path(workdir).name}"
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

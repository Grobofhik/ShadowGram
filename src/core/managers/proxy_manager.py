import os
import json
import uuid
import shutil
import urllib.request
import subprocess
import socket
import time
import zipfile
import string
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from src.core.constants import *
from src.core.logger import logger

def normalize_proxy_url(proxy_url: str) -> str:
    """Приводит прокси к стандартному виду scheme://user:pass@host:port"""
    if not proxy_url:
        return ""
    proxy_url = proxy_url.strip()
    
    # 1. Проверяем наличие префиксов
    prefix = ""
    for p in ["socks5://", "socks4://", "http://", "https://"]:
        if proxy_url.lower().startswith(p):
            prefix = p
            proxy_url = proxy_url[len(p):]
            break
            
    if not prefix:
        prefix = "http://"
        
    proxy_url = proxy_url.rstrip("/")
    
    # Формат: ip:port:user:pass
    parts = proxy_url.split(":")
    if len(parts) == 4:
        ip, port, user, password = parts
        return f"{prefix}{user}:{password}@{ip}:{port}"
        
    # Формат: ip:port
    elif len(parts) == 2:
        ip, port = parts
        return f"{prefix}{ip}:{port}"
        
    # Формат: user:pass@ip:port
    elif len(parts) == 3:
        user, pass_ip, port = parts
        if "@" in pass_ip:
            password, ip = pass_ip.split("@", 1)
            return f"{prefix}{user}:{password}@{ip}:{port}"
            
    return f"{prefix}{proxy_url}"


def parse_proxy_url(proxy_url: str) -> Optional[dict]:
    """Разбирает URL прокси в словарь для Hydrogram/Pyrogram/Proxychains"""
    if not proxy_url:
        return None
    try:
        proxy_url = normalize_proxy_url(proxy_url)
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)
        scheme = parsed.scheme or "http"
        
        default_ports = {"http": 80, "https": 443, "socks5": 1080, "socks4": 1080}
        port = parsed.port or default_ports.get(scheme, 80)
        
        hostname = parsed.hostname
        username = parsed.username
        password = parsed.password
        
        return {
            "scheme": scheme,
            "hostname": hostname,
            "port": port,
            "username": username,
            "password": password
        }
    except Exception as e:
        logger.error(f"Ошибка парсинга прокси {proxy_url}: {e}")
        return None


def _configure_socks_proxy_commands(
    tg_cmd: List[str], workdir: Path, proxy_info: dict
) -> List[str]:
    """Конфигурация SOCKS5/SOCKS4 прокси для Telegram Desktop без gost"""
    hostname = proxy_info["hostname"]
    port = proxy_info["port"]
    username = proxy_info.get("username")
    password = proxy_info.get("password")
    scheme = proxy_info.get("scheme", "socks5")
    
    if shutil.which("proxychains4"):
        pc_conf_path = workdir / "proxychains.conf"
        with open(pc_conf_path, "w") as f:
            f.write("strict_chain\n")
            f.write("proxy_dns\n")
            f.write("remote_dns_subnet 224\n")
            f.write("tcp_read_time_out 15000\n")
            f.write("tcp_connect_time_out 8000\n")
            f.write("[ProxyList]\n")
            if username and password:
                f.write(f"{scheme} {hostname} {port} {username} {password}\n")
            else:
                f.write(f"{scheme} {hostname} {port}\n")
        tg_cmd = ["proxychains4", "-f", str(pc_conf_path)] + tg_cmd

    tg_cmd.extend(["-proxy-server", f"{hostname}:{port}", "-proxy-type", scheme])
    return tg_cmd


def check_proxy_validity(proxy_url: Optional[str]) -> bool:
    """Проверка работоспособности HTTP/HTTPS/SOCKS5 прокси"""
    if not proxy_url:
        return False
    try:
        proxy_url = normalize_proxy_url(proxy_url)
        import requests
        proxies = {"http": proxy_url, "https": proxy_url}
        resp = requests.get("https://api.telegram.org", proxies=proxies, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        try:
            proxy_url = normalize_proxy_url(proxy_url)
            proxy_handler = urllib.request.ProxyHandler(
                {"http": proxy_url, "https": proxy_url}
            )
            opener = urllib.request.build_opener(proxy_handler)
            opener.open("https://api.telegram.org", timeout=5)
            return True
        except Exception as urllib_e:
            logger.error(f"Проверка прокси не удалась: {e} | urllib: {urllib_e}")
            return False


def _setup_gost_proxy(
    workdir: Path, proxy_url: str, local_port: int
) -> Optional[subprocess.Popen]:
    """Настройка Gost прокси"""
    try:
        log_path = workdir / "gost.log"
        with open(log_path, "w") as log_file:
            gost_process = subprocess.Popen(
                ["gost", "-L", f"socks5://127.0.0.1:{local_port}", "-F", proxy_url],
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
            )

        import time

        port_ready = False
        for _ in range(30):  # Максимум 3 секунды (30 * 0.1)
            if gost_process.poll() is not None:
                break
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.05)
                    if s.connect_ex(("127.0.0.1", local_port)) == 0:
                        port_ready = True
                        break
            except:
                pass
            time.sleep(0.1)

        if not port_ready or gost_process.poll() is not None:
            logger.error("gost упал или порт не открылся.")
            try:
                gost_process.terminate()
            except:
                pass
            return None

        return gost_process
    except Exception as e:
        logger.error(f"Ошибка прокси: {e}")
        return None


def _configure_proxy_commands(
    tg_cmd: List[str], workdir: Path, local_port: int
) -> List[str]:
    """Конфигурация прокси команд для Telegram"""
    if shutil.which("proxychains4"):
        pc_conf_path = workdir / "proxychains.conf"
        with open(pc_conf_path, "w") as f:
            f.write("strict_chain\n")
            f.write("proxy_dns\n")
            f.write("remote_dns_subnet 224\n")
            f.write("tcp_read_time_out 15000\n")
            f.write("tcp_connect_time_out 8000\n")
            f.write("[ProxyList]\n")
            f.write(f"socks5 127.0.0.1 {local_port}\n")
        tg_cmd = ["proxychains4", "-f", str(pc_conf_path)] + tg_cmd

    tg_cmd.extend(["-proxy-server", f"127.0.0.1:{local_port}", "-proxy-type", "socks5"])
    return tg_cmd



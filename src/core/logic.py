import json
import os
import shutil
import socket
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import tempfile

"""
Основная логика приложения.
Функции:

- get_free_port: получение свободного порта для прокси-туннеля
- export_backup: создание ZIP-архива с конфигурацией и сессиями
- import_backup: восстановление данных из ZIP-архива
- check_proxy_validity: проверка работоспособности HTTP/HTTPS прокси
- load_config: загрузка списка аккаунтов из config.json
- start_telegram: запуск процесса Telegram с привязкой к workdir и прокси
- stop_telegram: корректное завершение процессов Telegram и gost
- add_account: добавление новой записи об аккаунте в конфиг
- update_proxy: обновление URL прокси для конкретного аккаунта
- update_notes: сохранение заметок пользователя для аккаунта
- update_device_info: изменение имени устройства (hostname) для профиля
- remove_account: удаление аккаунта из конфигурации
- is_process_running: проверка, активен ли процесс в данный момент
- move_account_in_list: изменение позиции аккаунта в списке (сортировка)
- open_explorer: открытие папки аккаунта в файловом менеджере Thunar
- clear_cache: очистка временных файлов и кэша в папке профиля
- pack_selected_sessions: упаковка выбранных аккаунтов для отправки на сервер
- send_sessions_to_server: отправка архива на сервер
"""


def pack_selected_sessions(
    config_file: Union[str, Path],
    selected_workdirs: List[str],
    output_path: Union[str, Path]
) -> Tuple[bool, str]:
    """Упаковка только .session файлов выбранных аккаунтов и config.json для сервера"""
    try:
        config_file = Path(config_file)
        output_path = Path(output_path)

        data = _read_config(config_file)

        # Оставляем в конфиге только выбранные аккаунты
        server_config_data = {
            "settings": {}, 
            "accounts": [acc for acc in data.get("accounts", []) if acc["workdir"] in selected_workdirs]
        }

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Записываем урезанный конфиг во временный файл и добавляем в архив
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp_config:
                json.dump(server_config_data, tmp_config, indent=4, ensure_ascii=False)
                tmp_config_path = tmp_config.name
            
            zipf.write(tmp_config_path, "config.json")
            os.unlink(tmp_config_path)

            for acc in server_config_data["accounts"]:
                workdir = Path(acc["workdir"])
                if workdir.exists():
                    session_files = list(workdir.glob("*.session"))
                    avatar_file = workdir / "avatar.jpg"
                    if avatar_file.exists():
                        session_files.append(avatar_file)

                    for file_path in session_files:
                        arcname = f"accounts/{workdir.name}/{file_path.name}"
                        zipf.write(file_path, arcname)

        return True, "Архив для сервера успешно создан!"
    except Exception as e:
        return False, f"Ошибка сборки архива: {e}"

def send_sessions_to_server(
    zip_path: Union[str, Path],
    server_ip: str,
    server_port: str
) -> Tuple[bool, str]:
    """Отправка собранного ZIP-архива на сервер через /api/sessions/import"""
    try:
        import requests
        url = f"http://{server_ip}:{server_port}/api/sessions/import"
        with open(zip_path, 'rb') as f:
            files = {'file': (Path(zip_path).name, f, 'application/zip')}
            response = requests.post(url, files=files, timeout=30)
        
        if response.status_code == 200:
            return True, "Успешно отправлено на сервер!"
        else:
            return False, f"Ошибка сервера {response.status_code}: {response.text}"
    except ImportError:
        return False, "Не установлена библиотека requests. Установите 'pip install requests'"
    except Exception as e:
        return False, f"Сетевая ошибка при отправке: {e}"



BASE_DIR = Path(__file__).parent.parent.parent.absolute()
FARMS_DIR = BASE_DIR / "farms"
ACTIVE_FARM_FILE = BASE_DIR / "active_farm.txt"
CONFIG_FILE = BASE_DIR / "config.json"

def get_active_farm_name() -> str:
    """Возвращает имя текущей активной фермы"""
    if not ACTIVE_FARM_FILE.exists():
        return "default"
    try:
        return ACTIVE_FARM_FILE.read_text(encoding="utf-8").strip()
    except:
        return "default"

def get_active_farm_dir() -> Path:
    """Возвращает путь к папке текущей активной фермы"""
    farm_name = get_active_farm_name()
    farm_dir = FARMS_DIR / farm_name
    farm_dir.mkdir(parents=True, exist_ok=True)
    (farm_dir / "accounts").mkdir(parents=True, exist_ok=True)
    return farm_dir

def save_active_farm_config():
    """Синхронизирует root config.json с активной фермой"""
    try:
        active_farm = get_active_farm_name()
        farm_dir = FARMS_DIR / active_farm
        farm_dir.mkdir(parents=True, exist_ok=True)
        farm_config = farm_dir / "config.json"
        if CONFIG_FILE.exists():
            shutil.copy2(CONFIG_FILE, farm_config)
    except Exception as e:
        print(f"[ERROR] Ошибка синхронизации конфига фермы: {e}")

def init_farms():
    """Инициализация директорий ферм на старте приложения"""
    try:
        FARMS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Если нет файла активной фермы
        if not ACTIVE_FARM_FILE.exists():
            ACTIVE_FARM_FILE.write_text("default", encoding="utf-8")
            
        active_farm = get_active_farm_name()
        active_farm_dir = FARMS_DIR / active_farm
        active_farm_dir.mkdir(parents=True, exist_ok=True)
        (active_farm_dir / "accounts").mkdir(parents=True, exist_ok=True)
        
        farm_config = active_farm_dir / "config.json"
        
        # Миграция старого конфига
        if active_farm == "default" and not farm_config.exists() and CONFIG_FILE.exists():
            shutil.copy2(CONFIG_FILE, farm_config)
        
        # Если конфига фермы всё еще нет — создаем дефолтный
        if not farm_config.exists():
            default_config = {"settings": {"api_id": 0, "api_hash": ""}, "accounts": []}
            with open(farm_config, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
                
        # На старте всегда копируем конфиг активной фермы в корень
        shutil.copy2(farm_config, CONFIG_FILE)
    except Exception as e:
        print(f"[ERROR] Ошибка инициализации ферм: {e}")

def list_available_farms() -> List[str]:
    """Возвращает список имен всех доступных ферм"""
    if not FARMS_DIR.exists():
        return ["default"]
    farms = [d.name for d in FARMS_DIR.iterdir() if d.is_dir()]
    if not farms:
        return ["default"]
    return sorted(farms)

def create_new_farm(name: str) -> bool:
    """Создает новую ферму с текущими общими настройками, но без аккаунтов"""
    name = name.strip()
    if not name or "/" in name or "\\" in name:
        return False
    farm_dir = FARMS_DIR / name
    if farm_dir.exists():
        return False
        
    try:
        farm_dir.mkdir(parents=True, exist_ok=True)
        (farm_dir / "accounts").mkdir(parents=True, exist_ok=True)
        
        # Копируем текущие настройки (без аккаунтов)
        settings = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f).get("settings", {})
            except:
                pass
                
        default_config = {
            "settings": settings,
            "accounts": []
        }
        
        with open(farm_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка создания фермы: {e}")
        return False

def switch_active_farm(name: str) -> bool:
    """Переключает активную ферму"""
    name = name.strip()
    farm_config = FARMS_DIR / name / "config.json"
    if not farm_config.exists():
        return False
        
    try:
        # 1. Сохраняем текущую активную ферму
        save_active_farm_config()
        
        # 2. Переключаем имя в файле
        ACTIVE_FARM_FILE.write_text(name, encoding="utf-8")
        
        # 3. Копируем новый конфиг в корень
        shutil.copy2(farm_config, CONFIG_FILE)
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка переключения фермы: {e}")
        return False


_cached_config = None
_last_config_path = None
_last_mtime = 0

def _read_config(config_file: Path):
    global _cached_config, _last_config_path, _last_mtime
    if not config_file.exists():
        return {"settings": {}, "accounts": []}
    try:
        mtime = config_file.stat().st_mtime
        if _cached_config is not None and _last_config_path == config_file and _last_mtime == mtime:
            return _cached_config
        with open(config_file, "r", encoding="utf-8") as f:
            _cached_config = json.load(f)
            _last_config_path = config_file
            _last_mtime = mtime
            return _cached_config
    except:
        return {"settings": {}, "accounts": []}

def _write_config(config_file: Path, data):
    global _cached_config, _last_config_path, _last_mtime
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    _cached_config = data
    _last_config_path = config_file
    _last_mtime = config_file.stat().st_mtime
    save_active_farm_config()


def get_free_port() -> int:
    """Получает свободный порт для прокси-туннеля"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def export_backup(
    config_file: Union[str, Path], output_path: Union[str, Path]
) -> Tuple[bool, str]:
    """Создание ZIP-архива с конфигурацией и сессиями"""
    try:
        config_file = Path(config_file)
        output_path = Path(output_path)

        data = _read_config(config_file)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(config_file, "config.json")

            for acc in data.get("accounts", []):
                workdir = Path(acc["workdir"])
                if workdir.exists():
                    # Используем Path.glob для поиска файлов
                    session_files = list(workdir.glob("*.session"))
                    avatar_file = workdir / "avatar.jpg"

                    if avatar_file.exists():
                        session_files.append(avatar_file)

                    for file_path in session_files:
                        arcname = f"accounts/{workdir.name}/{file_path.name}"
                        zipf.write(file_path, arcname)

        return True, "Бэкап успешно создан!"
    except Exception as e:
        return False, f"Ошибка экспорта: {e}"


def import_backup(
    zip_path: Union[str, Path], current_config: Union[str, Path]
) -> Tuple[bool, str]:
    """Восстановление данных из ZIP-архива"""
    try:
        zip_path = Path(zip_path)
        current_config = Path(current_config)
        base_dir = current_config.parent

        with zipfile.ZipFile(zip_path, "r") as zipf:
            # Извлекаем файлы аккаунтов
            account_files = [f for f in zipf.namelist() if f.startswith("accounts/")]
            for member in account_files:
                zipf.extract(member, base_dir)

            # Извлекаем и обновляем конфиг
            zipf.extract("config.json", "/tmp")
            with open("/tmp/config.json", "r", encoding="utf-8") as f:
                new_data = json.load(f)

            with open(current_config, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)

        return True, "Данные успешно импортированы!"
    except Exception as e:
        return False, f"Ошибка импорта: {e}"


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
        print(f"[ERROR] Ошибка парсинга прокси {proxy_url}: {e}")
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
            print(f"Проверка прокси не удалась: {e} | urllib: {urllib_e}")
            return False


def load_config(config_file: Union[str, Path]) -> List[Dict[str, Any]]:
    """Загрузка списка аккаунтов из config.json"""
    try:
        config_file = Path(config_file)
        data = _read_config(config_file)
        return list(data.get("accounts", []))
    except Exception as e:
        print(f"Ошибка загрузки конфига: {e}")
        return []


def parse_vendor_model_from_device_name(device_name: str) -> Tuple[str, str]:
    if not device_name:
        return "PC", "Unknown"
    device_name_lower = device_name.lower()
    mapping = {
        "macbook": ("Apple", device_name.replace("-", " ")),
        "imac": ("Apple", device_name.replace("-", " ")),
        "mac-mini": ("Apple", "Mac mini"),
        "mac-studio": ("Apple", "Mac Studio"),
        "mac-pro": ("Apple", "Mac Pro"),
        "iphone": ("Apple", device_name.replace("-", " ")),
        "ipad": ("Apple", device_name.replace("-", " ")),
        "galaxy": ("Samsung", device_name.replace("-", " ")),
        "pixel": ("Google", device_name.replace("-", " ")),
    }
    for key, (vendor, model) in mapping.items():
        if device_name_lower.startswith(key):
            return vendor, model
            
    brands = ["dell", "lenovo", "asus", "hp", "acer", "msi", "razer", "microsoft", "xiaomi", "oneplus", "gigabyte", "apple", "samsung", "google"]
    parts = device_name.split("-", 1)
    if len(parts) == 2:
        brand, model = parts
        if brand.lower() in brands:
            brand_map = {
                "dell": "Dell", "lenovo": "Lenovo", "asus": "ASUS", "hp": "HP", "acer": "Acer",
                "msi": "MSI", "razer": "Razer", "microsoft": "Microsoft", "xiaomi": "Xiaomi",
                "oneplus": "OnePlus", "gigabyte": "GIGABYTE", "apple": "Apple", "samsung": "Samsung", "google": "Google"
            }
            clean_brand = brand_map.get(brand.lower(), brand)
            clean_model = model.replace("-", " ")
            return clean_brand, clean_model
            
    if "-" in device_name:
        parts = device_name.split("-")
        return parts[0], " ".join(parts[1:])
    return "PC", device_name


def get_or_create_fake_hw(account_name: Optional[str]) -> Tuple[str, str, Optional[str]]:
    import random
    from src.core.constants import CONFIG_FILE
    fake_vendor = None
    fake_model = None
    device_name = None
    
    if account_name:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            accounts = data.get("accounts", [])
            for acc in accounts:
                if acc.get("name") == account_name:
                    device_name = acc.get("device_name")
                    if device_name and device_name != f"PC-{account_name}":
                        fake_vendor, fake_model = parse_vendor_model_from_device_name(device_name)
                    else:
                        fake_vendor = acc.get("fake_vendor")
                        fake_model = acc.get("fake_model")
                        
                    if not fake_vendor or not fake_model:
                        vendors = ["ASUS", "Lenovo", "HP", "Acer", "GIGABYTE", "Apple", "Dell", "MSI"]
                        models = {
                            "ASUS": ["ZenBook UX430", "ROG Zephyrus G14", "VivoBook 15", "TUF Gaming A15"],
                            "Lenovo": ["ThinkPad T14", "Yoga Slim 7", "IdeaPad 3", "Legion 5"],
                            "HP": ["EliteBook 840", "Spectre x360", "Pavilion 14", "OMEN 15"],
                            "Acer": ["Swift 3", "Aspire 5", "Nitro 5", "Predator Helios"],
                            "GIGABYTE": ["Aero 15", "Aorus 15", "G5 KC"],
                            "Apple": ["MacBookPro16,1", "MacBookAir10,1", "MacBookPro18,2"],
                            "Dell": ["XPS 13", "Latitude 5420", "Inspiron 15", "G15 5511"],
                            "MSI": ["GS66 Stealth", "Prestige 14", "Modern 15"]
                        }
                        fake_vendor = random.choice(vendors)
                        fake_model = random.choice(models[fake_vendor])
                        
                        device_name = f"{fake_vendor}-{fake_model.replace(' ', '-')}"
                        acc["device_name"] = device_name
                        acc["fake_vendor"] = fake_vendor
                        acc["fake_model"] = fake_model
                        
                        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                        save_active_farm_config()
                    break
        except Exception as e:
            print(f"[WARNING] Ошибка загрузки/сохранения фейкового железа: {e}")
            
    if not fake_vendor or not fake_model:
        vendors = ["ASUS", "Lenovo", "HP", "Acer", "GIGABYTE", "Apple", "Dell", "MSI"]
        models = {
            "ASUS": ["ZenBook UX430", "ROG Zephyrus G14", "VivoBook 15", "TUF Gaming A15"],
            "Lenovo": ["ThinkPad T14", "Yoga Slim 7", "IdeaPad 3", "Legion 5"],
            "HP": ["EliteBook 840", "Spectre x360", "Pavilion 14", "OMEN 15"],
            "Acer": ["Swift 3", "Aspire 5", "Nitro 5", "Predator Helios"],
            "GIGABYTE": ["Aero 15", "Aorus 15", "G5 KC"],
            "Apple": ["MacBookPro16,1", "MacBookAir10,1", "MacBookPro18,2"],
            "Dell": ["XPS 13", "Latitude 5420", "Inspiron 15", "G15 5511"],
            "MSI": ["GS66 Stealth", "Prestige 14", "Modern 15"]
        }
        fake_vendor = random.choice(vendors)
        fake_model = random.choice(models[fake_vendor])
        device_name = f"{fake_vendor}-{fake_model.replace(' ', '-')}"
        
    return fake_vendor, fake_model, device_name


def start_telegram(
    workdir: Union[str, Path],
    proxy_url: Optional[str] = None,
    device_name: Optional[str] = None,
    account_name: Optional[str] = None,
) -> Tuple[Optional[subprocess.Popen], Optional[subprocess.Popen]]:
    """Запуск процесса Telegram с привязкой к workdir и прокси"""
    workdir = Path(workdir)
    print(f"\n[DEBUG] Запуск профиля: {workdir}")

    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch/generate fake hardware and device_name
    fake_vendor, fake_model, device_name_from_hw = get_or_create_fake_hw(account_name)
    if device_name_from_hw:
        device_name = device_name_from_hw

    gost_process: Optional[subprocess.Popen] = None
    tg_bin = (
        shutil.which("telegram-desktop")
        or shutil.which("Telegram")
        or "telegram-desktop"
    )
    tg_cmd = [tg_bin, "-workdir", str(workdir)]

    local_port: Optional[int] = None
    if proxy_url:
        proxy_url = normalize_proxy_url(proxy_url)
        is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
        if is_socks:
            proxy_info = parse_proxy_url(proxy_url)
            if proxy_info:
                tg_cmd = _configure_socks_proxy_commands(tg_cmd, workdir, proxy_info)
        else:
            local_port = get_free_port()
            gost_process = _setup_gost_proxy(workdir, proxy_url, local_port)
            if gost_process:
                tg_cmd = _configure_proxy_commands(tg_cmd, workdir, local_port)

    env = os.environ.copy()
    if proxy_url:
        is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
        if is_socks:
            env["all_proxy"] = proxy_url
            env["ALL_PROXY"] = proxy_url
        elif local_port:
            proxy_str = f"socks5://127.0.0.1:{local_port}"
            env["all_proxy"] = proxy_str
            env["ALL_PROXY"] = proxy_str

    if device_name:
        env.update(
            {
                "HOSTNAME": device_name,
                "QT_QPA_PLATFORM": "xcb",
            }
        )

    err_log = workdir / "telegram_error.log"
    
    # bwrap pipes setup
    pipes_fds = None
    r1, w1, r2, w2 = None, None, None, None
    
    if shutil.which("bwrap"):
        try:
            r1, w1 = os.pipe()
            r2, w2 = os.pipe()
            pipes_fds = (r1, r2)
        except Exception as pipe_e:
            print(f"[WARNING] Не удалось создать pipes для bwrap: {pipe_e}")
            pipes_fds = None

    final_cmd = _build_final_command(tg_cmd, device_name, fake_vendor, fake_model, pipes_fds)

    try:
        with open(err_log, "w") as f_err:
            if pipes_fds:
                tg_process = subprocess.Popen(
                    final_cmd, 
                    stdout=subprocess.DEVNULL, 
                    stderr=f_err, 
                    env=env,
                    pass_fds=pipes_fds
                )
                # Write fake data and close write ends
                os.write(w1, f"{fake_vendor}\n".encode())
                os.close(w1)
                os.write(w2, f"{fake_model}\n".encode())
                os.close(w2)
                
                # Close read ends in parent
                os.close(r1)
                os.close(r2)
            else:
                tg_process = subprocess.Popen(
                    final_cmd, stdout=subprocess.DEVNULL, stderr=f_err, env=env
                )
        return tg_process, gost_process
    except Exception as e:
        print(f"[ERROR] Критическая ошибка: {e}")
        if pipes_fds:
            for fd in [r1, r2, w1, w2]:
                try:
                    os.close(fd)
                except:
                    pass
        if gost_process:
            gost_process.terminate()
        return None, None


def stop_telegram(
    tg_process: Optional[subprocess.Popen],
    gost_process: Optional[subprocess.Popen] = None,
) -> bool:
    """Корректное завершение процессов Telegram и gost"""
    processes = [p for p in [tg_process, gost_process] if p is not None]
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                p.kill()
            except Exception:
                pass
        except Exception:
            pass
    return True


def add_account(
    config_file: Union[str, Path],
    name: str,
    workdir: Union[str, Path],
    proxy_url: Optional[str] = None,
    device_name: Optional[str] = None,
) -> bool:
    """Добавление новой записи об аккаунте в конфиг"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = {"accounts": []}
        if config_file.exists():
            data = _read_config(config_file)

        data["accounts"].append(
            {
                "name": name,
                "workdir": str(workdir),
                "proxy_url": proxy_url,
                "device_name": device_name if device_name else f"PC-{name}",
            }
        )

        _write_config(config_file, data)
        return True
    except Exception as e:
        print(f"Ошибка при добавлении аккаунта: {e}")
        return False


def update_proxy(
    config_file: Union[str, Path],
    workdir: Union[str, Path],
    new_proxy_url: Optional[str],
) -> bool:
    """Обновление URL прокси для конкретного аккаунта"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                acc["proxy_url"] = new_proxy_url
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        print(f"Ошибка при обновлении прокси: {e}")
        return False


def update_notes(
    config_file: Union[str, Path], workdir: Union[str, Path], new_notes: Optional[str]
) -> bool:
    """Сохранение заметок пользователя для аккаунта"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                acc["notes"] = new_notes
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        print(f"Ошибка при обновлении заметок: {e}")
        return False


def update_prompt(
    config_file: Union[str, Path], workdir: Union[str, Path], new_prompt: Optional[str]
) -> bool:
    """Сохранение индивидуального AI-промпта для аккаунта"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                acc["ai_prompt"] = new_prompt
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        print(f"Ошибка при обновлении промпта: {e}")
        return False


def update_device_info(
    config_file: Union[str, Path], workdir: Union[str, Path], device_name: str
) -> bool:
    """Изменение имени устройства (hostname) для профиля"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                acc["device_name"] = device_name
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        print(f"Ошибка при обновлении устройства: {e}")
        return False


def remove_account(config_file: Union[str, Path], workdir: Union[str, Path]) -> bool:
    """Удаление аккаунта из конфигурации"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        data["accounts"] = [
            acc for acc in data.get("accounts", []) if Path(acc["workdir"]) != workdir
        ]

        _write_config(config_file, data)
        return True
    except Exception as e:
        print(f"Ошибка при удалении аккаунта: {e}")
        return False


def is_process_running(process: Optional[subprocess.Popen]) -> bool:
    """Проверка, активен ли процесс в данный момент"""
    return process is not None and process.poll() is None


def move_account_in_list(
    config_file: Union[str, Path], workdir: Union[str, Path], direction: int
) -> bool:
    """Изменение позиции аккаунта в списке (сортировка)"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        accounts = data.get("accounts", [])
        idx = next(
            (i for i, acc in enumerate(accounts) if Path(acc["workdir"]) == workdir), -1
        )

        if idx == -1:
            return False

        new_idx = idx + direction
        if 0 <= new_idx < len(accounts):
            accounts[idx], accounts[new_idx] = accounts[new_idx], accounts[idx]
            _write_config(config_file, data)
            return True
        return False
    except Exception as e:
        print(f"Ошибка при перемещении: {e}")
        return False


def open_explorer(workdir: Union[str, Path]) -> bool:
    """Открытие папки аккаунта в файловом менеджере Thunar"""
    workdir = Path(workdir)
    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.Popen(["thunar", str(workdir)])
        return True
    except Exception as e:
        print(f"Ошибка открытия Thunar: {e}")
        return False


def clear_cache(workdir: Union[str, Path]) -> Tuple[bool, str]:
    """Очистка временных файлов и кэша в папке профиля"""
    workdir = Path(workdir)
    if not workdir.exists():
        return False, "Папка не существует"

    cache_dirs = ["cache", "media_cache", "thumbnails", "temp"]
    deleted_count = 0

    try:
        for cache_dir in cache_dirs:
            cache_path = workdir / cache_dir
            if cache_path.exists():
                shutil.rmtree(cache_path)
                deleted_count += 1
        return True, f"Успешно очищено {deleted_count} папок."
    except Exception as e:
        return False, str(e)


# Вспомогательные функции для start_telegram
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

        time.sleep(3) # Дать 3 секунды что бы запустился gost

        if gost_process.poll() is not None:
            print("[ERROR] gost упал.")
            return None

        return gost_process
    except Exception as e:
        print(f"[ERROR] Ошибка прокси: {e}")
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


def _build_final_command(
    tg_cmd: List[str],
    device_name: Optional[str],
    fake_vendor: Optional[str] = None,
    fake_model: Optional[str] = None,
    pipes_fds: Optional[Tuple[int, int]] = None
) -> List[str]:
    """Построение финальной команды для запуска"""
    if fake_vendor and fake_model and pipes_fds and shutil.which("bwrap"):
        r1, r2 = pipes_fds
        bwrap_cmd = [
            "bwrap",
            "--dev-bind", "/", "/",
            "--ro-bind-data", str(r1), "/sys/devices/virtual/dmi/id/sys_vendor",
            "--ro-bind-data", str(r2), "/sys/devices/virtual/dmi/id/product_name"
        ]
        if device_name:
            bwrap_cmd.extend(["--unshare-uts", "--hostname", device_name])
        return bwrap_cmd + tg_cmd

    if device_name and shutil.which("firejail"):
        firejail_cmd = [
            "firejail",
            "--noprofile",
            "--quiet",
            f"--hostname={device_name}",
            "--nodbus",
            "--env=DBUS_SESSION_BUS_ADDRESS=",
            "--env=DBUS_SYSTEM_BUS_ADDRESS=",
        ]
        return firejail_cmd + tg_cmd
    elif device_name and shutil.which("unshare"):
        set_hostname_py = (
            "import ctypes, socket; "
            "try: "
            "  libc=ctypes.CDLL('libc.so.6'); "
            f" name=b'{device_name}'; "
            "  libc.sethostname(name, len(name)); "
            "except Exception: pass"
        )
        inner_cmd = " ".join(f'"{c}"' for c in tg_cmd)
        return [
            "unshare",
            "--uts",
            "--map-root-user",
            "sh",
            "-c",
            f'python3 -c "{set_hostname_py}" && exec {inner_cmd}',
        ]
    else:
        return tg_cmd

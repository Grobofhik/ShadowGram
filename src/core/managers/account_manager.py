import os
import json
import uuid
import shutil
import urllib.request
import subprocess
import time
import zipfile
import string
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from src.core.constants import *
from src.core.managers.config_manager import load_config, _read_config, _write_config
from src.core.managers.hw_manager import get_or_create_fake_hw
from src.core.managers.proxy_manager import check_proxy_validity
from src.core.logger import logger

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


def add_account(
    config_file: Union[str, Path],
    name: str,
    workdir: Union[str, Path],
    proxy_url: Optional[str] = None,
    device_name: Optional[str] = None,
    api_id: Optional[str] = None,
    api_hash: Optional[str] = None,
) -> bool:
    """Добавление новой записи об аккаунте в конфиг"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = {"accounts": []}
        if config_file.exists():
            data = _read_config(config_file)

        if not device_name or device_name == f"PC-{name}":
            device_name = generate_random_device_name()

        account_record = {
            "name": name,
            "workdir": str(workdir),
            "proxy_url": proxy_url,
            "device_name": device_name,
        }
        
        if api_id:
            account_record["api_id"] = api_id
        if api_hash:
            account_record["api_hash"] = api_hash

        data["accounts"].append(account_record)

        _write_config(config_file, data)
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении аккаунта: {e}")
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
        logger.error(f"Ошибка при обновлении прокси: {e}")
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
        logger.error(f"Ошибка при обновлении заметок: {e}")
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
        logger.error(f"Ошибка при обновлении промпта: {e}")
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
        logger.error(f"Ошибка при обновлении устройства: {e}")
        return False


def get_hardware_profile(config_file: Union[str, Path], workdir: Union[str, Path]) -> dict:
    """Получает (или генерирует и сохраняет) аппаратный профиль устройства для аккаунта"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)
        
        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                if "hardware_profile" in acc and acc["hardware_profile"]:
                    return acc["hardware_profile"]
                
                # Если профиля нет, генерируем
                from src.core.managers.device_manager import generate_device_profile
                api_id = int(acc.get("api_id", data.get("api_id", 2040)))
                seed = acc.get("phone", str(workdir))
                
                profile = generate_device_profile(api_id, seed)
                acc["hardware_profile"] = profile
                _write_config(config_file, data)
                return profile
                
        # Если аккаунт не найден, генерируем на лету
        from src.core.managers.device_manager import generate_device_profile
        api_id = int(data.get("api_id", 2040))
        return generate_device_profile(api_id, str(workdir))
        
    except Exception as e:
        logger.error(f"Ошибка при получении hardware_profile: {e}")
        from src.core.managers.device_manager import generate_device_profile
        return generate_device_profile(2040, str(workdir))


def update_hardware_profile(
    config_file: Union[str, Path], workdir: Union[str, Path], profile: dict
) -> bool:
    """Изменение аппаратного профиля устройства (hardware_profile)"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                acc["hardware_profile"] = profile
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении аппаратного профиля: {e}")
        return False


def update_bound_channel(
    config_file: Union[str, Path], workdir: Union[str, Path], new_channel: Optional[str]
) -> bool:
    """Сохранение привязанного канала для аккаунта"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                acc["bound_channel"] = new_channel
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении привязанного канала: {e}")
        return False


def update_api_credentials(
    config_file: Union[str, Path], workdir: Union[str, Path], api_id: Optional[str], api_hash: Optional[str]
) -> bool:
    """Сохранение индивидуальных API данных для аккаунта"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                if api_id:
                    acc["api_id"] = api_id
                else:
                    acc.pop("api_id", None)
                    
                if api_hash:
                    acc["api_hash"] = api_hash
                else:
                    acc.pop("api_hash", None)
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении API данных: {e}")
        return False


def update_account_profile_data(
    config_file: Union[str, Path],
    workdir: Union[str, Path],
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    bio: Optional[str] = None,
    bound_channel: Optional[str] = None,
    username: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    channel_name: Optional[str] = None,
    channel_link: Optional[str] = None
) -> bool:
    """Сохранение профильных данных аккаунта в конфигурации"""
    try:
        config_file = Path(config_file)
        workdir = Path(workdir)

        data = _read_config(config_file)

        for acc in data.get("accounts", []):
            if Path(acc["workdir"]) == workdir:
                if first_name is not None: acc["first_name"] = first_name
                if last_name is not None: acc["last_name"] = last_name
                if bio is not None: acc["bio"] = bio
                if bound_channel is not None: acc["bound_channel"] = bound_channel
                if username is not None: acc["username"] = username
                if phone is not None: acc["phone"] = phone
                if email is not None: acc["email"] = email
                if password is not None: acc["password"] = password
                if channel_name is not None: acc["channel_name"] = channel_name
                if channel_link is not None: acc["channel_link"] = channel_link
                break

        _write_config(config_file, data)
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении профильных данных аккаунта: {e}")
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
        logger.error(f"Ошибка при удалении аккаунта: {e}")
        return False


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
        logger.error(f"Ошибка при перемещении: {e}")
        return False



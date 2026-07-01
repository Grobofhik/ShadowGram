import os
import json
import uuid
import shutil
import urllib.request
import subprocess
import tempfile
import time
import zipfile
import string
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from src.core.constants import *
from src.core.managers.farm_manager import save_active_farm_config
from src.core.logger import logger


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
    except Exception as e:
        bak_file = config_file.with_suffix(".json.bak")
        if bak_file.exists():
            try:
                with open(bak_file, "r", encoding="utf-8") as f:
                    _cached_config = json.load(f)
                    _last_config_path = config_file
                    _last_mtime = mtime
                    shutil.copy2(bak_file, config_file)
                    logger.warning(f"Config restored from backup due to read error: {e}")
                    return _cached_config
            except:
                pass
        logger.error(f"Failed to read config: {e}")
        return {"settings": {}, "accounts": []}


def _write_config(config_file: Path, data):
    global _cached_config, _last_config_path, _last_mtime
    config_file = Path(config_file)
    dir_path = config_file.parent
    
    if config_file.exists():
        try:
            shutil.copy2(config_file, config_file.with_suffix(".json.bak"))
        except Exception as e:
            logger.warning(f"Could not create backup config file: {e}")
            
    with tempfile.NamedTemporaryFile("w", dir=dir_path, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=4, ensure_ascii=False)
        temp_name = tf.name
        
    try:
        os.replace(temp_name, config_file)
    except Exception as e:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise e

    _cached_config = data
    _last_config_path = config_file
    _last_mtime = config_file.stat().st_mtime
    save_active_farm_config()
    
    # Зеркалируем данные в SQLite для дашборда и аналитики
    from src.core.managers.db_manager import mirror_to_sqlite
    mirror_to_sqlite(config_file, data)


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


def load_config(config_file: Union[str, Path]) -> List[Dict[str, Any]]:
    """Загрузка списка аккаунтов из config.json"""
    try:
        config_file = Path(config_file)
        data = _read_config(config_file)
        return list(data.get("accounts", []))
    except Exception as e:
        logger.error(f"Ошибка загрузки конфига: {e}")
        return []



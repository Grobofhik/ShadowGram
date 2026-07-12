import os
import json
from pathlib import Path
import sys

# Добавляем корень проекта в sys.path, если скрипт запускается напрямую
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.core.constants import CONFIG_FILE
from src.core.managers import config_manager

class FileScout:
    """
    Скаут для базовой проверки файлов профилей (Фаза 1).
    Не использует сеть, только читает файловую систему и конфиг.
    Цель: выявить статус аккаунтов (active, preparatory, incomplete).
    """
    def __init__(self):
        self.config_path = Path(CONFIG_FILE)
        
    def run_audit(self) -> dict:
        """Собирает первичный анамнез фермы (file-based)."""
        data = config_manager._read_config(self.config_path)
        accounts = data.get("accounts", [])
        
        farm_state = {}
        for acc in accounts:
            workdir = Path(acc.get("workdir", ""))
            acc_name = workdir.name
            
            state = {
                "workdir": str(workdir),
                "api_id": acc.get("api_id", ""),
                "phone": acc.get("phone", ""),
                "has_proxy": bool(acc.get("proxy_url") or acc.get("proxy")),
                "device_info_set": bool(acc.get("device_name") or acc.get("hardware_profile")),
                "has_session": False,
                "has_tdata": False,
                "status": "unknown",
                "reason": ""
            }
            
            # Проверяем наличие сессий в файловой системе
            if workdir.exists():
                session_files = list(workdir.glob("*.session"))
                if session_files:
                    state["has_session"] = True
                    
                tdata_path = workdir / "tdata"
                if tdata_path.exists() and tdata_path.is_dir():
                    state["has_tdata"] = True
                    
            # Логика статусов
            if state["has_session"] or state["has_tdata"]:
                state["status"] = "active"
                state["reason"] = "Ready for TG Scout"
            elif state["api_id"] and state["has_proxy"] and state["device_info_set"]:
                state["status"] = "preparatory"
                state["reason"] = "Missing .session or tdata file (Waiting for injection)"
            else:
                state["status"] = "incomplete"
                state["reason"] = "Missing core setup (API keys, Proxy, or Device Info)"
                
            farm_state[acc_name] = state
            
        return farm_state

if __name__ == "__main__":
    scout = FileScout()
    audit_result = scout.run_audit()
    print(json.dumps(audit_result, indent=2, ensure_ascii=False))

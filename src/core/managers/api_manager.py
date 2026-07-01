import hashlib
import random

OFFICIAL_APPS = [
    {"api_id": 2040, "api_hash": "b18441a1ff607e10a989891a5462e627"}, # Telegram Desktop
    {"api_id": 6, "api_hash": "eb06d4abfb49dc3eeb1aeb98ae0f581e"}, # Telegram Android
    {"api_id": 8, "api_hash": "7245de8e747a0d6fbe11f7ce14fcc0b5"}, # Telegram iOS
    {"api_id": 9, "api_hash": "259b1234ac24be4a5bbce012d908f023"}, # Telegram macOS
    {"api_id": 21724, "api_hash": "3e0cb5efcb523fc6abc49c5940640d44"} # Telegram X
]

def get_dynamic_api_credentials(seed_str: str) -> dict:
    """Генерирует пару api_id / api_hash на основе сида (workdir или phone)."""
    seed_int = int(hashlib.sha256(seed_str.encode('utf-8')).hexdigest(), 16) % (10**8)
    rnd = random.Random(seed_int)
    return rnd.choice(OFFICIAL_APPS)

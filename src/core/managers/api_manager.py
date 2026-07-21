import copy
import hashlib
import random
from typing import Dict, List


OFFICIAL_API_POOL = [
    {"api_id": 6, "api_hash": "eb06d4abfb49dc3eeb1aeb98ae0f581e", "name": "Android Official"},
    {"api_id": 2040, "api_hash": "b18441a1ff607e10a989891a5462e627", "name": "Desktop Official"},
    {"api_id": 10840, "api_hash": "33c45224029d59cb3889c8969766562b", "name": "iOS Official"},
    {"api_id": 2834, "api_hash": "68875f756c9b437a8b5b6a826bc42c03", "name": "macOS Official"},
    {"api_id": 2496, "api_hash": "8da85b0d5bfe62527e5b244c209159c3", "name": "WebK"},
    {"api_id": 14227303, "api_hash": "a09f7a731efbd9e7fc1fbb891a4b4e54", "name": "WebZ"},
    {"api_id": 21724, "api_hash": "3e0cb5efcd52300aec5994fdfc5bdc16", "name": "Android X"},
]


def _normalize_creds(api_id: int, api_hash: str) -> Dict[str, str]:
    return {"api_id": int(api_id), "api_hash": str(api_hash).strip()}


def get_official_api_pool() -> List[Dict[str, str]]:
    return copy.deepcopy(OFFICIAL_API_POOL)


def get_dynamic_api_credentials(seed_str: str) -> dict:
    """Возвращает детерминированную official API пару из локального vetted-списка."""
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16) % (10**8)
    rnd = random.Random(seed_int)
    return copy.deepcopy(rnd.choice(OFFICIAL_API_POOL))


def get_api_fallback_candidates(current_api_id: int, current_api_hash: str) -> List[Dict[str, str]]:
    """Возвращает список локальных official fallback-пар без текущей пары."""
    normalized_hash = str(current_api_hash).strip()
    candidates = []
    for creds in OFFICIAL_API_POOL:
        if int(creds["api_id"]) == int(current_api_id) and str(creds["api_hash"]).strip() == normalized_hash:
            continue
        candidates.append(copy.deepcopy(creds))
    return candidates


def is_invalid_api_error(error_text: str) -> bool:
    text = str(error_text).upper()
    markers = [
        "API_ID_INVALID",
        "API_ID_PUBLISHED_FLOOD",
        "API_ID_INVALID_X",
        "APP_ID_INVALID",
        "INVALID API",
        "THE API_ID/API_HASH COMBINATION IS INVALID",
        "API KEY INVALID",
        "API_ID FLOOD",
    ]
    return any(marker in text for marker in markers)

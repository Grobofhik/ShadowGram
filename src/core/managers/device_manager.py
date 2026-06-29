import hashlib
import random

def get_random_from_seed(seed_str: str):
    """Возвращает генератор Random, инициализированный сидом."""
    seed_int = int(hashlib.sha256(seed_str.encode('utf-8')).hexdigest(), 16) % (10**8)
    return random.Random(seed_int)

def generate_device_profile(api_id: int, seed: str) -> dict:
    """Генерирует согласованный профиль устройства на основе api_id и seed."""
    rnd = get_random_from_seed(seed)
    
    # Дефолтные значения (Desktop)
    device_model = "PC 64bit"
    system_version = "Windows 10"
    app_version = "4.8.4 x64"
    lang_code = "en"

    # API ID 2040, 17349, 10840 etc -> Desktop (Windows, MacOS, Linux)
    if api_id in [2040, 17349, 10840, 2496]:
        os_type = rnd.choices(["Windows", "macOS", "Linux"], weights=[80, 15, 5])[0]
        
        if os_type == "Windows":
            device_model = rnd.choice(["PC 64bit", "Desktop", "Windows PC"])
            system_version = rnd.choice(["Windows 10", "Windows 11"])
            app_version = rnd.choice(["4.8.4 x64", "4.8.5 x64", "4.9.0 x64"])
        elif os_type == "macOS":
            device_model = rnd.choice(["MacBook Pro", "MacBook Air", "iMac", "Mac mini"])
            system_version = rnd.choice(["macOS 12.6", "macOS 13.4", "macOS 14.0", "macOS 14.2"])
            app_version = rnd.choice(["9.6.1", "9.7.0", "10.0.1"])
        else:
            device_model = "PC 64bit"
            system_version = rnd.choice(["Ubuntu 22.04", "Ubuntu 20.04", "Arch Linux", "Debian 12"])
            app_version = rnd.choice(["4.8.4", "4.8.5"])
            
    # API ID 6 -> Android
    elif api_id == 6:
        brands = ["Samsung", "Xiaomi", "Google", "OnePlus", "Vivo", "Oppo"]
        brand = rnd.choices(brands, weights=[40, 30, 10, 5, 5, 10])[0]
        
        if brand == "Samsung":
            device_model = rnd.choice(["Galaxy S22", "Galaxy S23", "Galaxy S21 Ultra", "Galaxy A54", "Galaxy Z Fold 4"])
        elif brand == "Xiaomi":
            device_model = rnd.choice(["13 Pro", "12T", "Redmi Note 12", "Poco F5", "11 Lite"])
        elif brand == "Google":
            device_model = rnd.choice(["Pixel 7", "Pixel 7 Pro", "Pixel 6a", "Pixel 8"])
        else:
            device_model = f"{brand} Phone"
            
        system_version = rnd.choice(["SDK 31", "SDK 33", "SDK 34", "SDK 30"])
        app_version = rnd.choice(["10.1.1", "10.2.0", "9.7.6", "10.3.1"])
        
    # API ID 8 -> iOS
    elif api_id == 8:
        device_model = rnd.choice(["iPhone 13", "iPhone 13 Pro", "iPhone 14", "iPhone 14 Pro Max", "iPhone 15", "iPhone 12"])
        system_version = rnd.choice(["iOS 16.5", "iOS 17.0", "iOS 17.2", "iOS 16.1", "iOS 15.6"])
        app_version = rnd.choice(["10.1.1", "10.2.0", "9.7.0"])
        
    # macOS native app
    elif api_id == 9:
        device_model = rnd.choice(["MacBook Pro M1", "MacBook Air M2", "iMac", "Mac Studio"])
        system_version = rnd.choice(["macOS 13.5", "macOS 14.1", "macOS 14.3"])
        app_version = rnd.choice(["10.1.1", "10.2.0"])
        
    langs = ["ru", "en", "uk"]
    lang_code = rnd.choices(langs, weights=[70, 20, 10])[0]

    return {
        "device_model": device_model,
        "system_version": system_version,
        "app_version": app_version,
        "lang_code": lang_code
    }

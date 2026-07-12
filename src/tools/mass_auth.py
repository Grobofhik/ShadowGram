import asyncio
import os
from pathlib import Path
from hydrogram import Client
from hydrogram.errors import SessionPasswordNeeded

async def auth_accounts():
    print("=== Массовая авторизация аккаунтов (Hydrogram) ===")
    
    # Можно захардкодить свои данные или ввести в консоли
    api_id = input("Введите API_ID [по умолчанию 2040]: ").strip() or "2040"
    api_hash = input("Введите API_HASH [по умолчанию b18441a1ff607e10a989891a5462e627]: ").strip() or "b18441a1ff607e10a989891a5462e627"
    
    accounts_file = input("Введите путь к файлу с аккаунтами [accounts.txt]: ").strip() or "accounts.txt"
    if not os.path.exists(accounts_file):
        print(f"[!] Файл {accounts_file} не найден!")
        return

    sessions_dir = Path("sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)

    with open(accounts_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if not line.strip(): continue
        
        # Разделяем номер телефона и имя сессии (например: +1234567890,Account_1)
        parts = line.strip().split(',')
        phone = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else phone.replace('+', '')
        
        session_file = sessions_dir / f"{name}.session"
        if session_file.exists():
            print(f"[#] Сессия для {name} ({phone}) уже существует в {sessions_dir}. Пропуск.")
            continue

        print(f"\n--- Настройка аккаунта: {name} ({phone}) ---")
        
        # В Hydrogram сессии сохраняются в workdir под именем {name}.session
        client = Client(
            name=name,
            api_id=int(api_id),
            api_hash=api_hash,
            workdir=str(sessions_dir)
        )
        
        try:
            await client.connect()
            sent_code = await client.send_code(phone)
            
            code = input(f"Введите код из Telegram для {phone}: ")
            
            try:
                await client.sign_in(phone, sent_code.phone_code_hash, code)
            except SessionPasswordNeeded:
                password = input(f"Введите 2FA пароль для {phone}: ")
                await client.check_password(password)
                
            me = await client.get_me()
            print(f"[V] Аккаунт {me.first_name} успешно подключен! Файл: {session_file}")
            
        except Exception as e:
            print(f"[!] Ошибка с аккаунтом {phone}: {e}")
        finally:
            if client.is_connected:
                await client.disconnect()

    print(f"\n[!] Все аккаунты из списка обработаны. Сессии сохранены в папке '{sessions_dir}'.")

if __name__ == "__main__":
    try:
        asyncio.run(auth_accounts())
    except KeyboardInterrupt:
        print("\n[!] Процесс прерван пользователем.")

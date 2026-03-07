# <img src="resources/icons/GrobTyan_logo.png" width="60" valign="middle"> ShadowGram

<p align="center">
  <img src="image.png" width="700" alt="ShadowGram Interface">
</p>

**ShadowGram** — это мощная платформа для управления аккаунтами Telegram и автоматизации маркетинговых активностей. Проект сочетает в себе глубокую изоляцию профилей, продвинутую систему асинхронных плагинов и эстетичный интерфейс на базе PyQt6.

---

## <img src="resources/icons/succure_icon.png" width="20" valign="middle"> Основные возможности

### <img src="resources/icons/start_icon.png" width="20" valign="middle"> Управление аккаунтами
- **Изоляция:** Каждый профиль работает в своей директории (`workdir`), не пересекаясь с другими.
- **Shadow Proxy:** Прозрачное туннелирование трафика через `gost`. Система создает индивидуальный SOCKS5-мост для каждой сессии.
- **Безопасность:** Поддержка индивидуальных имен устройств (Device Name) для каждой сессии.

### <img src="resources/icons/moduls_icon.png" width="20" valign="middle"> Система плагинов
Уникальная архитектура позволяет запускать сложные сценарии автоматизации:
- **Параллельное выполнение:** Запуск задач на десятках аккаунтов одновременно с полной изоляцией ресурсов.
- **Staggered Start:** Умные задержки между запусками аккаунтов для обхода алгоритмов детекции Telegram.
- **Циклы и Ротации:** Автоматические циклы «Работа — Сон» для поддержания активности 24/7.
- **Динамический UI:** Автоматическая генерация полей настроек на основе параметров плагина.

### <img src="resources/icons/folder_icon.png" width="20" valign="middle"> База знаний (Wiki)
В приложении реализована встроенная **интерактивная документация**. Найти её можно в разделе **Настройки (<img src="resources/icons/settings_icon.png" width="16" valign="middle">) -> 📖 Документация**. 
Там вы найдете подробные гайды по:
- Установке и первому запуску.
- Работе с профилями и прокси.
- Инструкции ко всем модулям автоматизации.
- Руководство по разработке собственных плагинов.

---

## <img src="resources/icons/folder_icon.png" width="20" valign="middle"> Доступные плагины
*Подробную документацию по каждому модулю можно найти в папке [documentation/modules/](documentation/modules/).*

- <img src="resources/icons/rocket_icon.png" width="18" valign="middle"> **Smart Warmer:** Интеллектуальный прогрев через чаты, чтение и пересылку постов.
- <img src="resources/icons/view_icon.png" width="18" valign="middle"> **Channel Viewer:** Массовая накрутка просмотров на сообщения в каналах.
- <img src="resources/icons/succure_icon.png" width="18" valign="middle"> **Privacy Guard:** Мгновенная настройка жесткой приватности аккаунтов.
- <img src="resources/icons/note_icon.png" width="18" valign="middle"> **Set Avatar:** Быстрая установка фото профиля.
- <img src="resources/icons/device_icon.png" width="18" valign="middle"> **Get Auth Code:** Перехват кодов подтверждения из системных чатов.
- <img src="resources/icons/search_icon.png" width="18" valign="middle"> **Session Check:** Диагностика банов и валидация сессий с обновлением аватаров.

---

## <img src="resources/icons/settings_icon.png" width="20" valign="middle"> Системные зависимости

Для корректной работы функций проксирования и изоляции в системе должны быть установлены следующие утилиты:

- **[gost](https://github.com/ginuerzh/gost):** Создание SOCKS5-туннелей для каждого аккаунта.
- **firejail:** Изоляция имен устройств и сетевого окружения (опционально, но рекомендуется).
- **proxychains-ng (proxychains4):** Форсированное проксирование трафика Telegram Desktop.
- **thunar:** Файловый менеджер для быстрого открытия папок профилей.

---

## <img src="resources/icons/save_icon.png" width="20" valign="middle"> Установка и запуск (Arch Linux)

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/scaramouche/ShadowGram.git
   cd ShadowGram
   ```

2. **Установите системные зависимости:**
   ```bash
   sudo pacman -S gost firejail proxychains-ng thunar
   ```

3. **Создайте и настройте виртуальное окружение:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Запустите приложение:**
   ```bash
   python ShadowGram.py
   ```

---

## <img src="resources/icons/folder_icon.png" width="20" valign="middle"> Структура проекта

```text
ShadowGram/
├── ShadowGram.py          # Главная точка входа (GUI)
├── resources/             # Иконки, звуки и шрифты
├── documentation/         # Интерактивная база знаний (START, Modules, Developers)
├── src/
│   ├── core/              # Ядро системы (логика, константы, менеджер модулей)
│   ├── modules/           # Плагины и асинхронные чекеры
│   └── ui/                # Интерфейс PyQt6 (страницы, окна, стили)
└── config.json            # Файл конфигурации (создается автоматически)
```

---

**Разработано с акцентом на стабильность, асинхронность и удобство автоматизации. <img src="resources/icons/server_icon.png" width="20" valign="middle">**

---

<img src="resources/icons/cancel_icon.png" width="20" valign="middle"> **Отказ от ответственности:** Проект находится в стадии **активной разработки**. Автор не несет ответственности за возможную блокировку, утерю ваших аккаунтов Telegram или любые другие последствия, возникшие в результате использования данного программного обеспечения. Используйте на свой страх и риск.

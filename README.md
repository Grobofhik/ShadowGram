# ShadowGram

ShadowGram — desktop GUI для управления Telegram-аккаунтами, сессиями, фермами, прокси и плагинами автоматизации.

Проект написан на `PyQt6`. Основная работа идёт вокруг локальных Telegram-сессий в папках аккаунтов и модулей из `src/modules/plugins`.

## Что умеет

- вести несколько ферм через `farms/<farm_name>`
- хранить аккаунты, прокси, заметки, device/app metadata
- создавать сессии через `Hydrogram` или `Telethon`
- запускать плагины по аккаунтам локально или через ServerGram
- делать backup/import конфигов и сессий
- работать с proxy pool
- вести документацию прямо внутри UI

## Структура данных

- `config.json` — активный конфиг
- `active_farm.txt` — имя активной фермы
- `farms/<farm>/config.json` — конфиг конкретной фермы
- `farms/<farm>/accounts/<profile>/` — папка профиля
- `farms/<farm>/accounts/<profile>/*.session` — Telegram session
- `farms/<farm>/accounts/<profile>/avatar.jpg` — локальная копия аватарки
- `backups/` — ZIP-бэкапы

## Основные страницы UI

- `Аккаунты` — список профилей, поиск, массовые действия
- `Создать` — быстрое создание профиля
- `Дашборд` — обзор здоровья фермы
- `Таблица` — табличная работа с профилями
- `Сервер` — отправка сессий и запуск плагинов через ServerGram
- `Модули` — локальный запуск плагинов
- `Нейрокомм.` / `Ассистент` / `Сценарист` — AI и сценарии
- `Доп. сервисы` — session auth, fallback API, конвертеры
- `Документация` — встроенный просмотрщик markdown
- `Настройки` — API, AI, фермы, proxy pool, backup, безопасность

## Установка

Минимум:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ShadowGram.py
```

Практически проект также использует:

- `telethon` — для Telethon-сессий
- `requests` — сетевые запросы и части UI
- `pyqtgraph` — элементы dashboard
- `gost` — HTTP/HTTPS proxy tunnel для части операций

Если чего-то нет, смотри [documentation/troubleshooting/errors.md](documentation/troubleshooting/errors.md).

## Создание профиля

У каждого аккаунта есть:

- имя профиля
- рабочая папка
- proxy
- `api_id` / `api_hash`
- device / app / lang metadata
- заметки и AI prompt

Если `api_id/api_hash` не заданы у профиля, при создании подставляются глобальные `default_tg_api_id/default_tg_api_hash` из настроек. Случайные "сгенерированные" ключи больше не являются основным источником.

## Авторизация сессии

Кнопка `Авторизовать (Войти)` в главном окне открывает мастер:

- имя файла сессии по умолчанию берётся из имени профиля
- папка по умолчанию — папка аккаунта
- если файл уже существует, старт блокируется
- можно выбрать `Hydrogram` или `Telethon`
- после старта показываются логи, поле кода, затем поле `2FA`, если нужно
- процесс можно отменить на любой стадии

При создании используются данные профиля:

- `api_id` / `api_hash`
- proxy
- device model
- system version
- app version
- system lang code
- lang pack / lang code

## Fallback API

В проекте есть локальный пул fallback API в `src/core/managers/api_manager.py`. Он не тянется из интернета и не обещает вечную валидность.

Логика:

- сначала используются ключи аккаунта
- затем глобальные ключи из настроек
- при ошибках вида `API_ID_INVALID` или `API_ID_PUBLISHED_FLOOD` авторизация может перебрать локальные fallback-пары

Надёжный путь всё равно один: свои `api_id/api_hash` из `my.telegram.org`.

## Плагины

Плагины лежат в `src/modules/plugins`. Каждый плагин наследует `BaseModule` и описывает:

- `MODULE_NAME`
- `MODULE_DESC`
- `PARAMS`
- режим одиночного или параллельного запуска
- цикличность
- задержки старта и повторов

Список модулей и описание: [documentation/modules/README.md](documentation/modules/README.md)

## Фермы

Ферма — изолированный набор аккаунтов и настроек.

- переключение ферм меняет активный `config.json`
- новая ферма наследует текущие настройки, но не аккаунты
- аккаунты хранятся внутри своей фермы

Подробно: [documentation/START.md](documentation/START.md)

## Важно

- проект хранит реальные Telegram-сессии на диске
- backup ZIP может включать `.session`
- при работе через HTTP/HTTPS proxy нужен `gost`
- часть функций зависит от валидности API-ключей и живых прокси

## Быстрые ссылки

- [Старт и навигация](documentation/START.md)
- [Первый запуск](documentation/getting_started/first_start.md)
- [Создание профиля](documentation/profiles/create_profile.md)
- [Действия с профилями](documentation/profiles/profile_actions.md)
- [Глобальные настройки](documentation/settings/global_settings.md)
- [Сценарии использования](documentation/features/scenarios.md)
- [Антибан-практика](documentation/best_practices/anti_ban.md)
- [ServerGram](documentation/server/server_setup.md)
- [Ошибки и решения](documentation/troubleshooting/errors.md)
- [Гайд по плагинам](documentation/developers/plugin_development_guide.md)

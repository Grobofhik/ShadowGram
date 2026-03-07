# <img src="../../resources/icons/moduls_icon.png" width="32" valign="middle"> Руководство разработчика плагинов

ShadowGram построен на модульной архитектуре. Это означает, что любую новую функцию автоматизации можно оформить в виде отдельного Python-файла (плагина), который приложение подхватит автоматически.

---

## 🏗 Архитектура системы

Все плагины в ShadowGram являются наследниками базового класса `BaseModule`. Благодаря этому разработчику не нужно заботиться о:
*   Поиске файлов сессий и авторизации.
*   Поднятии прокси-туннелей через `gost`.
*   Сложной логике многопоточности и управления задачами.

### Где лежат плагины?
Все файлы плагинов должны находиться в директории:
`src/modules/plugins/`

---

## 🛠 Справочник BaseModule

При создании плагина вы переопределяете ключевые атрибуты и методы.

### Ключевые атрибуты (Metadata)
*   `MODULE_NAME`: Строка. Имя модуля, которое увидит пользователь в списке.
*   `MODULE_DESC`: Строка. Краткое описание функционала.
*   `SINGLE_ACCOUNT`: Boolean. Если `True`, модуль запрещает массовый выбор аккаунтов (полезно для ручных инструментов).
*   `PARAMS`: Список словарей. Описывает поля ввода для UI.
    *   Пример: `{"name": "count", "type": "text", "label": "Кол-во сообщений"}`

### Жизненный цикл (Task Lifecycle)
Эти параметры критически важны для массовой автоматизации:
*   `START_DELAY`: Кортеж `(min, max)`. Задержка в секундах перед самым первым запуском. Помогает избежать одновременного входа 100 аккаунтов в сеть.
*   `IS_CYCLIC`: Boolean. Если `True`, после завершения метода `run` аккаунт уснет и запустится снова через время `CYCLE_DELAY`.
*   `CYCLE_DELAY`: Кортеж `(min, max)`. Время сна между циклами выполнения (в секундах).

---

## 🔌 Основные методы и инструменты

### 1. `await self.init_client()`
Всегда вызывайте этот метод первым делом в `run()`. Он:
1.  Находит `.session` файл в папке аккаунта.
2.  Запускает `gost` для прокси (если прокси привязан).
3.  Создает и подключает экземпляр `hydrogram.Client`.
4.  Возвращает `True` при успехе.

### 2. `self.client`
Это ваш главный инструмент. Полноценный клиент Hydrogram (MTProto).
Примеры использования:
```python
# Получить информацию о себе
me = await self.client.get_me()

# Отправить сообщение
await self.client.send_message("username", "Hello from ShadowGram!")

# Вступить в чат
await self.client.join_chat("https://t.me/example")
```

### 3. `self.log(message, status="info")`
Метод для вывода информации в консоль приложения.
*   `status="info"`: Белый текст (по умолчанию).
*   `status="success"`: <span style="color: #00e676;">Зеленый</span> (успех).
*   `status="warning"`: <span style="color: #fbc02d;">Желтый</span> (внимание).
*   `status="error"`: <span style="color: #ff5252;">Красный</span> (ошибка).

### 4. `self.acc`
Словарь с данными текущего аккаунта:
*   `self.acc['name']`: Название профиля.
*   `self.acc['workdir']`: Путь к папке профиля.
*   `self.acc['proxy_url']`: Строка прокси.

---

## 🧪 Пример идеального плагина

Создадим простой модуль для отправки сообщений:

```python
import asyncio
import random
from src.core.base_module import BaseModule

class SimpleSpammer(BaseModule):
    MODULE_NAME = "📩 Простой рассыльщик"
    MODULE_DESC = "Рассылает сообщение по списку чатов."
    
    # UI Параметры
    PARAMS = [
        {"name": "chats", "type": "textarea", "label": "Список чатов (каждый с новой строки)"},
        {"name": "message", "type": "text", "label": "Текст сообщения"}
    ]

    async def run(self, **kwargs):
        # 1. Инициализация
        if not await self.init_client():
            return

        # 2. Получение данных из UI
        chats = kwargs.get("chats", "").strip().split("\n")
        text = kwargs.get("message", "Привет!")

        try:
            for chat in chats:
                chat = chat.strip()
                if not chat: continue
                
                self.log(f"Отправка в {chat}...", "info")
                await self.client.send_message(chat, text)
                self.log(f"Успешно отправлено в {chat}!", "success")
                
                # Имитация человеческой паузы
                await asyncio.sleep(random.uniform(5, 10))
                
        except Exception as e:
            self.log(f"Критическая ошибка: {e}", "error")
        finally:
            # 3. Всегда вызывайте cleanup для закрытия сессии и прокси
            await self.cleanup()
```

---

## ⚠️ Обработка ошибок

При написании логики обязательно импортируйте и обрабатывайте стандартные ошибки Hydrogram:
*   `hydrogram.errors.FloodWait`: Возникает при слишком частых запросах. Обязательно делайте `await asyncio.sleep(e.value)`.
*   `hydrogram.errors.UserDeactivated`: Аккаунт забанен.
*   `hydrogram.errors.Unauthorized`: Сессия стала невалидной.

---

<img src="../../resources/icons/rocket_icon.png" width="32" valign="middle"> **ShadowGram** — это гибкая платформа. Создавайте свои уникальные инструменты и автоматизируйте Telegram на полную мощность!

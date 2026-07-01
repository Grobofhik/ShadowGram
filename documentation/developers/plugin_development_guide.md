# 💻 Разработка собственных модулей

ShadowGram обладает открытой архитектурой (Plugin API), позволяющей разработчикам на Python создавать собственные сценарии для автоматизации действий. 

Все пользовательские модули загружаются автоматически при старте приложения, если они расположены в директории `src/modules/`.

---

## 🏗 Базовая структура модуля

Каждый модуль должен наследоваться от базового класса `BaseModule` и реализовывать асинхронный метод `run()`.

```python
from src.core.base_module import BaseModule
import asyncio

class MyCustomModule(BaseModule):
    name = "💡 Мой кастомный модуль"
    description = "Краткое описание того, что делает плагин."
    
    # Определение полей для графического интерфейса
    fields = [
        {"name": "target_username", "label": "Юзернейм цели:", "type": "text", "default": "@durov"},
        {"name": "delay", "label": "Задержка (сек):", "type": "number", "default": "5"}
    ]

    async def run(self, client, config):
        """
        Основной метод выполнения.
        :param client: Объект hydrogram.Client (уже авторизованный)
        :param config: Словарь с параметрами, переданными из UI
        """
        target = config.get("target_username")
        delay = int(config.get("delay", 5))

        self.log(f"Начинаем работу с {target}...")
        
        # Пример: Отправка сообщения
        try:
            await client.send_message(target, "Привет из ShadowGram!")
            self.log(f"✅ Сообщение успешно отправлено!", level="success")
        except Exception as e:
            self.log(f"❌ Ошибка отправки: {e}", level="error")
            
        await asyncio.sleep(delay)
        self.log("Работа модуля завершена.")
```

## 🛠 API и Инструменты

### Логирование
Вместо стандартного `print()` всегда используйте встроенный метод `self.log()`. Это гарантирует, что ваше сообщение появится в графическом интерфейсе пользователя (в Консоли) и будет записано в системные логи.
*   `level="info"` (по умолчанию)
*   `level="success"` (зеленый текст)
*   `level="error"` (красный текст)
*   `level="warning"` (желтый текст)

### Объект `client`
Модулю передается полностью инициализированный и подключенный к прокси клиент `hydrogram.Client`. Вы можете использовать все стандартные методы Hydrogram API (например, `client.join_chat()`, `client.get_messages()`, `client.resolve_peer()`).

### Взаимодействие с UI
Список `fields` определяет, какие элементы управления будут показаны пользователю при выборе вашего модуля:
*   `text`: Однострочное текстовое поле (QLineEdite).
*   `number`: Поле ввода только чисел.
*   `textarea`: Многострочное поле для списков или больших текстов.
*   `checkbox`: Галочка (True/False).

## 🚀 Деплой
Просто сохраните ваш скрипт как `my_module.py` в папку `src/modules/` и перезапустите ShadowGram. Если синтаксических ошибок нет, ваш плагин автоматически появится в левом меню!

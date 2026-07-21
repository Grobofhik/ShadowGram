# Разработка плагинов

## Где лежат плагины

Локальные плагины грузятся из:

```text
src/modules/plugins/
```

Менеджер ищет `*.py`, импортирует модуль и ищет классы-наследники `BaseModule`.

## Минимальный каркас

```python
from src.core.base_module import BaseModule

class MyModule(BaseModule):
    MODULE_NAME = "Мой модуль"
    MODULE_DESC = "Что делает модуль."
    PARAMS = []

    def run(self):
        self.log("Старт")
        client = self.init_client()
        try:
            # работа
            pass
        finally:
            self.cleanup()
```

## Важные поля

- `MODULE_NAME`
- `MODULE_DESC`
- `PARAMS`
- `SINGLE_ACCOUNT`
- `ALLOW_PARALLEL`
- `START_DELAY`
- `IS_CYCLIC`
- `CYCLE_DELAY`

## Что даёт `BaseModule`

- доступ к данным аккаунта
- `init_client()` с созданием Hydrogram-клиента
- proxy routing
- поддержку HTTP/HTTPS proxy через `gost`
- `sleep()` с учётом `stealth_mode`
- логирование
- cleanup клиента и proxy tunnel

## Данные аккаунта внутри модуля

Обычно доступны:

- `self.account`
- `self.workdir`
- `self.proxy_url`
- `self.device_name`
- `self.api_id`
- `self.api_hash`

## Формат `PARAMS`

Проект использует UI-описание параметров. Смотри реальные примеры в существующих плагинах:

- `follower.py`
- `ai_commenter.py`
- `channel_monitor.py`
- `smart_warmer.py`

## Практические правила

- всегда вызывать `cleanup()`
- не обещать UI-параметры, которых нет в `PARAMS`
- не жёстко кодировать чужие пути
- уважать flood wait и timeout
- писать понятные логи для пользователя

import importlib.util
import traceback
from pathlib import Path
from typing import Dict, Optional, Type

from src.core.base_module import BaseModule


class ModuleManager:
    def __init__(self):
        # Определяем путь к плагинам относительно этого файла
        self.plugins_dir = Path(__file__).parent.parent / "modules" / "plugins"
        self.modules: Dict[str, Type[BaseModule]] = {}
        self._loaded_modules: Dict[str, any] = {}  # Кэш загруженных модулей

    def discover_modules(self) -> Dict[str, Type[BaseModule]]:
        """Сканирует папку плагинов и подгружает классы, наследуемые от BaseModule"""
        self.modules.clear()

        if not self.plugins_dir.exists():
            self._log(f"Директория не найдена: {self.plugins_dir}")
            return self.modules

        self._log(f"Сканирование: {self.plugins_dir}")

        # Используем Path.glob для более эффективного поиска
        python_files = list(self.plugins_dir.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py"]

        for module_path in python_files:
            filename = module_path.name
            module_name = f"src.modules.plugins.{filename[:-3]}"

            # Проверяем кэш перед загрузкой
            if module_name in self._loaded_modules:
                self._extract_module_classes(
                    self._loaded_modules[module_name], filename
                )
                continue

            try:
                module_obj = self._load_module(module_name, module_path)
                if module_obj:
                    self._loaded_modules[module_name] = module_obj
                    self._extract_module_classes(module_obj, filename)

            except Exception as e:
                self._log_error(f"Ошибка загрузки {filename}", e)

        return self.modules

    def get_module_class(self, display_name: str) -> Optional[Type[BaseModule]]:
        """Получает класс модуля по имени"""
        return self.modules.get(display_name)

    def get_all_modules(self) -> Dict[str, Type[BaseModule]]:
        """Возвращает все найденные модули"""
        return self.modules.copy()

    def reload_module(self, display_name: str) -> bool:
        """Перезагружает конкретный модуль"""
        if display_name not in self.modules:
            return False

        # Находим соответствующий файл и перезагружаем
        for module_name, module_obj in self._loaded_modules.items():
            if hasattr(module_obj, display_name):
                try:
                    importlib.reload(module_obj)
                    self._extract_module_classes(
                        module_obj,
                        Path(
                            module_name.replace("src.modules.plugins.", "") + ".py"
                        ).name,
                    )
                    self._log(f"Модуль {display_name} перезагружен")
                    return True
                except Exception as e:
                    self._log_error(f"Ошибка перезагрузки {display_name}", e)
                    return False
        return False

    def _load_module(self, module_name: str, module_path: Path) -> Optional[any]:
        """Загружает модуль по пути"""
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(module_path))
            if spec is None or spec.loader is None:
                return None

            module_obj = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module_obj)
            return module_obj
        except Exception:
            return None

    def _extract_module_classes(self, module_obj: any, filename: str) -> None:
        """Извлекает классы BaseModule из загруженного модуля"""
        found_any = False

        # Используем comprehension для более чистого кода
        base_module_classes = [
            getattr(module_obj, attr_name)
            for attr_name in dir(module_obj)
            if self._is_valid_module_class(getattr(module_obj, attr_name))
        ]

        for attr in base_module_classes:
            display_name = getattr(attr, "MODULE_NAME", filename[:-3])
            self.modules[display_name] = attr
            self._log(f"Загружен плагин: {display_name}")
            found_any = True

        if not found_any:
            self._log(
                f"WARNING: В файле {filename} не найдено классов BaseModule", "warning"
            )

    def _is_valid_module_class(self, attr: any) -> bool:
        """Проверяет, является ли атрибут валидным классом модуля"""
        return (
            isinstance(attr, type)
            and issubclass(attr, BaseModule)
            and attr is not BaseModule
        )

    def _log(self, message: str, level: str = "info") -> None:
        """Логирование с унифицированным форматом"""
        prefix = "[MANAGER]"
        if level == "warning":
            prefix = "[MANAGER WARNING]"
        elif level == "error":
            prefix = "[MANAGER ERROR]"
        print(f"{prefix} {message}")

    def _log_error(self, message: str, error: Exception) -> None:
        """Логирование ошибок с traceback"""
        self._log(f"{message}: {error}", "error")
        traceback.print_exc()

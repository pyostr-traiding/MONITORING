# app/core/registry.py
import pkgutil
import importlib
import inspect
from pathlib import Path


def _import_all_modules_from_package(package_name: str):
    """
    Гарантированно импортирует все модули внутри пакета (включая подкаталоги).
    Это нужно, чтобы классы были реально загружены в память
    до вызова inspect.getmembers().
    """
    package = importlib.import_module(package_name)
    package_path = Path(package.__file__).parent

    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
        full_name = f"{package_name}.{module_name}"
        try:
            importlib.import_module(full_name)
        except Exception as e:
            print(f"[Registry] ⚠ Ошибка импорта модуля {full_name}: {e}")

        # Если внутри подпакет — импортируем рекурсивно
        if is_pkg:
            _import_all_modules_from_package(full_name)


def discover_subclasses(package_name: str, base_class: type):
    """
    Ищет все классы, являющиеся подклассами base_class внутри пакета.
    """
    _import_all_modules_from_package(package_name)

    subclasses = []
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, base_class) and obj is not base_class:
                subclasses.append(obj)

    return subclasses


def load_handlers():
    """Возвращает список всех Handler-классов"""
    from app.handlers.base_handler import BaseHandler
    handlers = discover_subclasses("app.handlers", BaseHandler)
    print(f"[Registry] Загружено обработчиков: {len(handlers)}")
    return handlers


def load_triggers():
    """Возвращает список всех Trigger-классов"""
    from app.triggers.base_trigger import BaseTrigger
    triggers = discover_subclasses("app.triggers", BaseTrigger)
    print(f"[Registry] Загружено триггеров: {len(triggers)}")
    return triggers

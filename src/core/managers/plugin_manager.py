import os
import sys
import importlib.util

# Global registry for custom plugins
custom_specs = {}
custom_handlers = {}

def load_custom_nodes():
    global custom_specs, custom_handlers
    
    # Path to custom_nodes in the root of the src directory
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dir_path = os.path.join(root_dir, "custom_nodes")
    
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        # Create a template file to guide the user
        template_path = os.path.join(dir_path, "example_node.py.template")
        with open(template_path, "w", encoding="utf-8") as f:
            f.write('''# Пример кастомного плагина для ShadowGram
# Для активации переименуйте файл в example_node.py

# 1. Спецификация UI блока
NODE_SPEC = {
    "custom_example_action": {
        "title": "Пример плагина",
        "category": "Плагины",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "message_text": {"label": "Текст сообщения", "type": "str", "default": "Привет из плагина!"}
        }
    }
}

# 2. Логика выполнения (Action Handler)
async def handler(executor, params):
    # Получаем разрешенный параметр
    text = executor.resolve_string(params.get("message_text", ""))
    
    # Логируем действие в консоль редактора
    executor.log(f"Плагин запущен! Текст: {text}", "success")
    
    # Передаем управление следующему блоку
    return "next"
''')

    for filename in os.listdir(dir_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            file_path = os.path.join(dir_path, filename)
            try:
                # Dynamically load the python file as a module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                
                # Add directory to sys.path to resolve local imports in plugins
                if dir_path not in sys.path:
                    sys.path.insert(0, dir_path)
                    
                spec.loader.exec_module(module)
                
                if hasattr(module, "NODE_SPEC") and hasattr(module, "handler"):
                    node_spec = getattr(module, "NODE_SPEC")
                    for action_name, action_spec in node_spec.items():
                        # Force category to "Плагины" to keep them clean
                        action_spec["category"] = "Плагины"
                        custom_specs[action_name] = action_spec
                        custom_handlers[action_name] = getattr(module, "handler")
            except Exception as e:
                print(f"Error loading custom node from {filename}: {e}")

# Load custom nodes on import
load_custom_nodes()

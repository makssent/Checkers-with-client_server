import json
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
import socket

saved_user_id = None

def connect_to_server(client_socket):
    server_address = ('172.20.10.2', 43000)  # IP адрес и порт сервера
    client_socket.connect(server_address)

def login():
    username = username_entry.get()
    password = password_entry.get()

    if not username or not password:
        messagebox.showerror("Input Error", "Username and Password cannot be empty.")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_to_server(client_socket)
    login_data = json.dumps({'username': username, 'password': password, 'command': 1})
    client_socket.sendall(login_data.encode())
    response = client_socket.recv(1024).decode()
    try:
        response_data = json.loads(response)
        if response_data:
            status = response_data['status']
            if status:
                user_id = response_data['user_id']
                global saved_user_id
                saved_user_id = user_id
                root.withdraw()  # Скрытие окна регистрации и авторизации
                subprocess.Popen([sys.executable, 'main_activity.py', str(saved_user_id)])
            else:
                messagebox.showerror("Login Error", response_data['message'])
        else:
            messagebox.showerror("Login Error", "Invalid response format")
    except json.JSONDecodeError:
        messagebox.showerror("Login Error", "Failed to decode server response")

    client_socket.close()

def register():
    username = username_entry.get()
    password = password_entry.get()

    if not username or not password:
        messagebox.showerror("Input Error", "Username and Password cannot be empty.")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_to_server(client_socket)
    register_data = json.dumps({'username': username, 'password': password, 'command': 2})
    client_socket.sendall(register_data.encode())
    response = client_socket.recv(1024).decode()
    try:
        response_data = json.loads(response)
        if response_data:
            status = response_data['status']
            if status:
                messagebox.showinfo("Registration Success", "User registered successfully")
                user_id = response_data['user_id']
                global saved_user_id
                saved_user_id = user_id
                root.withdraw()  # Скрытие окна регистрации и авторизации
                subprocess.Popen([sys.executable, 'main_activity.py', str(saved_user_id)])
            else:
                messagebox.showerror("Registration Error", response_data['message'])
        else:
            messagebox.showerror("Registration Error", "Invalid response format")
    except json.JSONDecodeError:
        messagebox.showerror("Registration Error", "Failed to decode server response")

    client_socket.close()

# Создание основного окна
root = tk.Tk()
root.title("Authorize Window")
root.geometry("400x300")
root.configure(bg='#2E8B57')
root.resizable(False, False)  # Запрещаем изменение размера окна

# Центрирование окна
window_width = 400
window_height = 300
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

position_top = int(screen_height / 2 - window_height / 2)
position_right = int(screen_width / 2 - window_width / 2)

root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

# Заголовок
title_label = tk.Label(root, text="Авторизация", font=("Helvetica", 18, "bold"), bg='#2E8B57', fg='white')
title_label.pack(pady=10)

# Метки и поля ввода для имени пользователя и пароля
tk.Label(root, text="Username:", bg='#2E8B57', fg='white').pack(pady=5)
username_entry = tk.Entry(root, width=30)
username_entry.pack(pady=5)

tk.Label(root, text="Password:", bg='#2E8B57', fg='white').pack(pady=5)
password_entry = tk.Entry(root, show='*', width=30)
password_entry.pack(pady=5)

# Кнопки для входа и регистрации
button_style = {"font": ("Helvetica", 10), "width": 15, "bg": "lightblue"}

tk.Button(root, text="Login", **button_style, command=login).pack(pady=5)
tk.Button(root, text="Register", **button_style, command=register).pack(pady=5)

# Запуск главного цикла
root.mainloop()

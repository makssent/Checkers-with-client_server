import socket
import subprocess
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox

if len(sys.argv) > 1:
    data = json.loads(sys.argv[1])
    user_id = data['user_id']
    room_data = data.get('message', [])
    error_message = data.get('error_message', '')
else:
    print("No data provided.")
    sys.exit(1)


def main(room_data):
    root = tk.Tk()
    root.title("Просмотр Комнат")
    root.geometry("600x400")
    root.configure(bg='#2E8B57')
    root.resizable(False, False)

    # Центрирование окна
    window_width = 600
    window_height = 400
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)

    root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    # Заголовок
    title_label = tk.Label(root, text="Просмотр Комнат", font=("Helvetica", 24, "bold"), bg='#2E8B57', fg='white')
    title_label.pack(pady=20)

    # Если есть сообщение об ошибке, отображаем его
    if error_message:
        messagebox.showerror("Ошибка", error_message)

    # Настройка стиля
    style = ttk.Style()
    style.configure("Custom.Treeview",
                    background="#2E8B57",
                    fieldbackground="#2E8B57",
                    foreground="white",
                    rowheight=25)
    style.configure("Custom.Treeview.Heading",
                    background="#2E8B57",
                    foreground="#4CAF50",
                    font=("Helvetica", 10, "bold"))

    style.map('Custom.Treeview', background=[('selected', '#4CAF50')], foreground=[('selected', 'white')])

    # Создание Treeview с прокруткой
    columns = ('Room ID', 'Creator', 'Players')
    tree = ttk.Treeview(root, columns=columns, show='headings', style="Custom.Treeview")
    tree.heading('Room ID', text='Room ID')
    tree.heading('Creator', text='Creator')
    tree.heading('Players', text='Players')

    tree.column('Room ID', width=50, anchor=tk.CENTER, stretch=False)
    tree.column('Creator', width=300, anchor=tk.CENTER, stretch=False)
    tree.column('Players', width=250, anchor=tk.CENTER, stretch=False)

    for room in room_data:
        players_formatted = f"{room['player_count']}/2"
        tree.insert('', tk.END, values=(room['room_id'], room['creator'], players_formatted))

    tree.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def go_back():
        root.destroy()
        subprocess.Popen([sys.executable, 'main_activity.py', str(user_id)])

    # Кнопка "Назад"
    back_button = tk.Button(root, text="Назад", command=go_back, font=("Helvetica", 14), bg='#4CAF50', fg='white')
    back_button.pack(side=tk.LEFT, padx=10, pady=10)

    def connect_to_server(client_socket):
        server_address = ('172.20.10.2', 43000)  # IP адрес и порт сервера
        client_socket.connect(server_address)

    # Функция для кнопки "Обновить"
    def refresh_rooms():
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
                        # Очистка текущих данных в Treeview
                        for item in tree.get_children():
                            tree.delete(item)
                        # Вставка обновленных данных
                        for room in message:
                            players_formatted = f"{room['player_count']}/2"
                            tree.insert('', tk.END, values=(room['room_id'], room['creator'], players_formatted))
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
        root.after(5000, refresh_rooms)

    # Кнопка "Обновить"
    refresh_button = tk.Button(root, text="Обновить", command=refresh_rooms, font=("Helvetica", 14), bg='#4CAF50', fg='white')
    refresh_button.pack(side=tk.RIGHT, padx=10, pady=10)

    def create_room():
        root.withdraw()
        subprocess.Popen(
            [sys.executable, 'client.py', json.dumps({'user_id': user_id, 'create_room': 1})])

    # Кнопка "Создать комнату"
    create_button = tk.Button(root, text="Создать комнату", command=create_room, font=("Helvetica", 14), bg='#4CAF50', fg='white')
    create_button.pack(side=tk.RIGHT, padx=10, pady=10)

    # Кнопка "Войти"
    def join_room():
        selected_items = tree.selection()
        if selected_items:
            item = selected_items[0]
            item_data = tree.item(item, "values")
            players_count = int(item_data[2].split('/')[0])
            if players_count < 2:
                room_id = item_data[0]
                root.withdraw()
                subprocess.Popen([sys.executable, 'client.py', json.dumps({'user_id': user_id, 'room_number': room_id})])
            else:
                messagebox.showwarning("Вход в комнату", "Комната заполнена")

    join_button = tk.Button(root, text="Войти", command=join_room, font=("Helvetica", 14), bg='#4CAF50', fg='white')
    join_button.pack(side=tk.RIGHT, padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main(room_data)

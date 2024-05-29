import subprocess
import sys
import json
import tkinter as tk
from tkinter import ttk

if len(sys.argv) > 1:
    data = json.loads(sys.argv[1])
    user_id = data['user_id']
    player_data = data['message']
else:
    print("No data provided.")
    sys.exit(1)

def main(player_data):
    root = tk.Tk()
    root.title("Топ Игроков")
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
    title_label = tk.Label(root, text="Топ Игроков", font=("Helvetica", 24, "bold"), bg='#2E8B57', fg='white')
    title_label.pack(pady=20)

    # Настройка стиля
    style = ttk.Style()
    style.configure("Custom.Treeview",
                    background="#2E8B57",
                    fieldbackground="#2E8B57",
                    foreground="white",
                    rowheight=25)
    style.configure("Custom.Treeview.Heading",
                    background="#2E8B57",
                    foreground="#4CAF50",  # Изменен цвет текста для заголовков столбцов
                    font=("Helvetica", 10, "bold"))

    style.map('Custom.Treeview', background=[('selected', '#4CAF50')], foreground=[('selected', 'white')])

    # Создание Treeview с прокруткой
    columns = ('#', 'Nickname', 'Score')
    tree = ttk.Treeview(root, columns=columns, show='headings', style="Custom.Treeview")
    tree.heading('#', text='#')
    tree.heading('Nickname', text='Nickname')
    tree.heading('Score', text='Score')

    tree.column('#', width=50, anchor=tk.CENTER)
    tree.column('Nickname', width=300, anchor=tk.CENTER)
    tree.column('Score', width=250, anchor=tk.CENTER)

    for index, player in enumerate(player_data):
        parts = player.split(': ')
        position = parts[0]
        nickname = parts[1]
        score = parts[2]
        tree.insert('', tk.END, values=(position, nickname, score))

    # Блокировка редактирования ячеек
    tree.bind('<Button-1>', lambda e: 'break')

    tree.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Функция для кнопки "Назад"
    def go_back():
        root.destroy()
        subprocess.Popen([sys.executable, 'main_activity.py', str(user_id)])

    # Кнопка "Назад"
    back_button = tk.Button(root, text="Назад", command=go_back, font=("Helvetica", 14), bg='#4CAF50', fg='white')
    back_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main(player_data)

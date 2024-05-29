import json
import socket
import subprocess
import sys
import time
import pygame
import select

# Размеры
CELL_SIZE = 80  # размер одной клетки в пикселях
BOARD_SIZE = 8  # размер доски 8x8

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (213, 50, 80)
GREY = (170, 215, 81)
BLUE = (0, 0, 255)  # цвет обводки для выбранной шашки
GREEN = (0, 255, 0)  # цвет подсветки возможных ходов

user_id = None
my_client_number = None
selected_piece = None  # Для хранения позиции выбранной шашки
possible_moves = []  # Список возможных ходов для выбранной шашки
pieces = [[0] * 8 for _ in range(8)]
my_turn = False  # Переменная для отслеживания хода игрока
turn_start_time = 0  # Время начала текущего хода

# Глобальные переменные для хранения информации об игроках
my_username = ""
my_score = 0
opponent_username = ""
opponent_score = 0
show_rdy_button = False  # Глобальный флаг для отображения кнопки готовности
is_pressed = False
toggle = False  # Переключатель состояния

pygame.init()
screen = pygame.display.set_mode((880, 640))  # Увеличили ширину для боковой панели
font = pygame.font.SysFont(None, 55)
endgame = False
game_status = 0
winner_username = ""
rdy_check_player = False  # Статус готовности игрока


def main():
    global selected_piece, my_turn, user_id, turn_start_time, my_username, my_score, opponent_username, opponent_score, show_rdy_button, rdy_check_player, is_pressed, toggle, my_client_number

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    create_room = 0
    room_number_connect = 0
    if len(sys.argv) > 1:
        try:
            data = json.loads(sys.argv[1])
            user_id = data.get('user_id')
            if not user_id:
                print("Error: user_id not provided")
                sys.exit(1)
            create_room = int(data.get('create_room', 0))
            room_number_connect = int(data.get('room_number', 0))
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON")
            sys.exit(1)
    else:
        print("Error: No arguments provided")
        sys.exit(1)

    if user_id is None:
        print("Error: user_id is required")
        sys.exit(1)

    connect_to_server(client_socket)

    waiting_rdy_check = True
    print(user_id)
    try:
        if create_room == 1:
            send_data = json.dumps({'command': 4, 'user_id': user_id})
            print("my_user_id", user_id)
            print("Sending data:", send_data)
            client_socket.sendall(send_data.encode())
        elif room_number_connect != 0:
            data = json.dumps({"user_id": user_id, 'room_number': room_number_connect, 'command': 6})
            client_socket.sendall(data.encode())
        else:
            data = json.dumps({"user_id": user_id}).encode()
            client_socket.sendall(data)

        response = client_socket.recv(1024).decode()
        response_json = json.loads(response)
        if response_json.get('status') == False:
            error_message = response_json.get('message', 'Unknown error')
            subprocess.Popen(
                [sys.executable, 'looking_rooms.py', json.dumps({'user_id': user_id, "error_message": error_message})])
            sys.exit(1)
        else:
            client_number = response_json.get('client_number')
            print('Мой номер:', client_number)
            my_client_number = client_number

            if int(client_number) == 1:
                my_turn = True

            room_number = response_json.get('room_number')
            print('Комната:', room_number)

        # Начальное состояние доски
        setup_pieces(pieces)

        while waiting_rdy_check:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()  # Завершаем текущий процесс Python
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    exit_button = draw_exit_button()
                    rdycheck_button = draw_rdycheck_button() if show_rdy_button else None
                    if exit_button.collidepoint(mouse_pos):
                        pygame.quit()
                        subprocess.Popen([sys.executable, 'main_activity.py', user_id])
                        sys.exit()
                        return
                    if rdycheck_button and rdycheck_button.collidepoint(mouse_pos):
                        toggle = not toggle
                        rdy_check_player = toggle
                        is_pressed = toggle
                        data = json.dumps({
                            'status': toggle,
                            'room_number': room_number,
                            'client_number': client_number
                        })
                        client_socket.sendall(data.encode())

            screen.fill(BLACK)
            draw_waiting_screen(show_rdy_button)
            pygame.display.flip()

            # Использование select для неблокирующего ожидания данных от сервера
            ready_to_read, _, _ = select.select([client_socket], [], [], 0.1)
            if ready_to_read:
                start_command = client_socket.recv(1024).decode()
                if start_command:
                    step_response_data = json.loads(start_command)
                    message_start = step_response_data.get('message_start')
                    players = step_response_data.get('players', [])
                    for player in players:
                        if player['player_number'] == int(client_number):
                            my_username = player['username']
                            my_score = player['score']
                            opponent_username = player['opponent_username']
                            opponent_score = player['opponent_score']
                    if message_start == "RdyCheck":
                        show_rdy_button = True  # Показываем кнопку готовности
                    elif message_start == "StartGame":
                        waiting_rdy_check = False  # Выходим из цикла ожидания
                        turn_start_time = time.time()  # Устанавливаем время начала хода

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    exit_button = draw_exit_button()
                    if exit_button.collidepoint(mouse_pos):
                        running = False
                        pygame.quit()  # Завершаем работу Pygame перед запуском нового процесса
                        subprocess.Popen([sys.executable, 'main_activity.py', user_id])
                    elif my_turn:
                        handle_click(event.pos, client_socket, client_number, room_number)

            draw_board()
            draw_pieces(pieces)
            draw_game_info(client_socket, room_number)
            pygame.display.flip()

            # Использование select для неблокирующего ожидания данных от сервера
            if not my_turn and not endgame:
                ready_to_read, _, _ = select.select([client_socket], [], [], 0.1)
                if ready_to_read:
                    wait_opponent(client_socket)

            if endgame:
                running = False
                display_winner(game_status)
                subprocess.Popen([sys.executable, 'main_activity.py', str(user_id)])

    except Exception as e:
        print("An error occurred:", e)

    finally:
        # Закрываем соединение
        client_socket.close()

def draw_game_info_before_start_game():
    global my_turn, winner_username, endgame, my_username, my_score, opponent_username, opponent_score
    info_x = BOARD_SIZE * CELL_SIZE + 20
    pygame.draw.rect(screen, GREY, (BOARD_SIZE * CELL_SIZE, 0, 240, 640))

    # Отображение информации об игроках
    small_font = pygame.font.Font(None, 24)

    # Колонка с информацией о вас
    my_info_text = small_font.render(f"Вы:", True, BLACK)
    screen.blit(my_info_text, (info_x, 20))
    my_username_text = small_font.render(my_username, True, BLACK)
    screen.blit(my_username_text, (info_x, 50))
    my_score_text = small_font.render(f"Очки: {my_score}", True, BLACK)
    screen.blit(my_score_text, (info_x, 80))

    # Колонка с информацией о противнике
    opponent_info_text = small_font.render(f"Противник:", True, BLACK)
    screen.blit(opponent_info_text, (info_x + 100, 20))
    opponent_username_text = small_font.render(opponent_username, True, BLACK)
    screen.blit(opponent_username_text, (info_x + 100, 50))
    opponent_score_text = small_font.render(f"Очки: {opponent_score}", True, BLACK)
    screen.blit(opponent_score_text, (info_x + 100, 80))

    draw_rdycheck_button()
    draw_exit_button()

def connect_to_server(client_socket):
    server_address = ('172.20.10.2', 43000)  # IP адрес и порт сервера
    client_socket.connect(server_address)

def setup_pieces(pieces):
    for row in range(8):
        for col in range(8):
            if (row + col) % 2 == 1:
                if row < 3:
                    pieces[row][col] = 1  # Красные шашки в верхних рядах
                elif row > 4:
                    pieces[row][col] = 2  # Белые шашки в нижних рядах

# Инвертирование координат для игрока 1
def invert_coordinates(row, col):
    if int(my_client_number) == 1:
        return 7 - row, 7 - col
    return row, col

# Изменим функцию draw_pieces, чтобы она учитывала инвертированные координаты
def draw_pieces(pieces):
    global selected_piece
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            piece_row, piece_col = invert_coordinates(row, col)
            if pieces[piece_row][piece_col] != 0:
                center = (col * CELL_SIZE + CELL_SIZE // 2, row * CELL_SIZE + CELL_SIZE // 2)
                color = RED if pieces[piece_row][piece_col] == 1 else WHITE
                pygame.draw.circle(screen, color, center, CELL_SIZE // 2 - 10)
                if selected_piece == (piece_row, piece_col):
                    pygame.draw.circle(screen, BLUE, center, CELL_SIZE // 2 - 5, 5)

# Изменим функцию draw_board, чтобы она учитывала инвертированные координаты
def draw_board():
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            board_row, board_col = invert_coordinates(row, col)
            color = WHITE if (board_row + board_col) % 2 == 0 else BLACK
            pygame.draw.rect(screen, color, (col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            if (board_row, board_col) in possible_moves:
                center = (col * CELL_SIZE + CELL_SIZE // 2, row * CELL_SIZE + CELL_SIZE // 2)
                pygame.draw.circle(screen, GREEN, center, CELL_SIZE // 4)

def draw_waiting_screen(need_button):
    # Затемняем игровое поле
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            color = (50, 50, 50) if (row + col) % 2 == 0 else (20, 20, 20)
            pygame.draw.rect(screen, color, (col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE))

    # Отрисовка затемненного информационного окна
    draw_info_panel(need_button)
    text_info = ""
    size = 0
    if need_button:
        text_info = 'Waiting Game'
        size = 100
    else:
        text_info = 'Waiting Search Opponent'
        size = 70
    # Отрисовка надписи
    large_font = pygame.font.SysFont(None, size)  # Увеличиваем размер шрифта
    text = large_font.render(text_info, True, WHITE)
    text_rect = text.get_rect(center=(BOARD_SIZE * CELL_SIZE // 2, BOARD_SIZE * CELL_SIZE // 2))
    screen.blit(text, text_rect)

rdy_check_player = False  # Статус готовности игрока
button_pressed_color = (100, 200, 100)  # Цвет нажатой кнопки
button_normal_color = BLACK  # Обычный цвет кнопки
def draw_rdycheck_button():
    button_font = pygame.font.SysFont(None, 50)
    button_color = button_pressed_color if is_pressed else button_normal_color
    rdycheck_button = pygame.Rect(BOARD_SIZE * CELL_SIZE + 60, 400, 120, 50)
    pygame.draw.rect(screen, button_color, rdycheck_button)
    text_surface = button_font.render('Готов?', True, WHITE)
    text_rect = text_surface.get_rect(center=rdycheck_button.center)
    screen.blit(text_surface, text_rect)
    return rdycheck_button

def draw_exit_button():
    button_font = pygame.font.SysFont(None, 50)
    exit_button = pygame.Rect(BOARD_SIZE * CELL_SIZE + 60, 500, 120, 50)
    pygame.draw.rect(screen, BLACK, exit_button)
    text_surface = button_font.render('Выход', True, WHITE)
    text_rect = text_surface.get_rect(center=exit_button.center)
    screen.blit(text_surface, text_rect)
    return exit_button

def draw_info_panel(need_button):
    info_x = BOARD_SIZE * CELL_SIZE + 20
    pygame.draw.rect(screen, GREY, (BOARD_SIZE * CELL_SIZE, 0, 240, 640))
    draw_exit_button()  # Добавляем кнопку "Выход"
    if need_button:
        draw_game_info_before_start_game()

def handle_click(pos, client_socket, client_number, room_number):
    global selected_piece, possible_moves, pieces, my_turn, endgame, game_status, turn_start_time
    col = pos[0] // 80
    row = pos[1] // 80

    if col >= BOARD_SIZE:  # Игнорируем клики вне доски
        return

    row, col = invert_coordinates(row, col)  # Инвертируем координаты клика
    if (row, col) in possible_moves and possible_moves != []:
        data = json.dumps(
            {'row': row, 'col': col, 'client_number': client_number, 'pieces': pieces, 'selected_piece': selected_piece,
             'operation': 2, 'room_number': room_number}
        )
        client_socket.send(data.encode())
        step_response = client_socket.recv(1024).decode()  # Блокирующий вызов
        if step_response:
            step_response_data = json.loads(step_response)
            pieces = step_response_data.get('pieces', pieces)
            continue_step = step_response_data['continue_step']
            game_status = int(step_response_data['game_status'])
            possible_moves = []
            selected_piece = None
            if game_status == 0:
                if continue_step == False:
                    my_turn = False
                turn_start_time = time.time()  # Перезапускаем таймер
            elif game_status in [1, 2]:
                global winner_username
                winner_username = step_response_data['winner_username']
                endgame = True
                return  # Выходим из цикла после победы
    else:
        data = json.dumps(
            {'row': row, 'col': col, 'client_number': client_number, 'pieces': pieces, 'selected_piece': selected_piece,
             'operation': 1, 'room_number': room_number}
        )
        client_socket.send(data.encode())
        while True:
            response = client_socket.recv(1024).decode()  # Блокирующий вызов
            if response:
                response_data = json.loads(response)
                selected_item = response_data.get('selected_item')
                if selected_item is not None:
                    selected_piece = tuple(response_data.get('selected_item', []))
                    take_possibles(client_socket)
                else:
                    possible_moves = []
                    selected_piece = None
            break

def take_possibles(client_socket):
    global possible_moves
    client_socket.sendall("Received".encode())
    while True:
        response = client_socket.recv(1024).decode()  # Блокирующий вызов
        if response:
            response_data = json.loads(response)
            possible_moves = [tuple(move) for move in response_data.get('possible_moves', [])]
            draw_board()
        break

def wait_opponent(client_socket):
    global pieces, my_turn, endgame, game_status, turn_start_time
    while True:
        ready_to_read, _, _ = select.select([client_socket], [], [], 0.1)
        if ready_to_read:
            opponent_step = client_socket.recv(1024)
            if opponent_step:
                opponent_step_data = json.loads(opponent_step)
                pieces = opponent_step_data.get('pieces', pieces)
                game_status = int(opponent_step_data['game_status'])
                if game_status == 0:
                    continue_step = opponent_step_data['continue_step']
                    if continue_step == False:
                        my_turn = True
                        turn_start_time = time.time()  # Перезапускаем таймер
                elif game_status in [1, 2]:
                    global winner_username
                    winner_username = opponent_step_data['winner_username']
                    endgame = True
                    return
                break

def display_winner(game_status):
    screen.fill(BLACK)
    font = pygame.font.Font(None, 74)
    color = RED if game_status == 1 else WHITE
    congratulation_text = font.render("Congratulations!", True, color)
    winner_text = font.render(f"{winner_username} wins!", True, color)
    congratulation_text_rect = congratulation_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 50))
    winner_text_rect = winner_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 50))
    screen.blit(congratulation_text, congratulation_text_rect)
    screen.blit(winner_text, winner_text_rect)
    pygame.display.flip()
    pygame.time.wait(5000)

def draw_game_info(client_socket, room_number):
    global my_turn, winner_username, endgame, my_username, my_score, opponent_username, opponent_score, turn_start_time
    info_x = BOARD_SIZE * CELL_SIZE + 20
    pygame.draw.rect(screen, GREY, (BOARD_SIZE * CELL_SIZE, 0, 240, 640))

    # Отображение информации об игроках
    small_font = pygame.font.Font(None, 24)

    # Колонка с информацией о вас
    my_info_text = small_font.render(f"Вы:", True, BLACK)
    screen.blit(my_info_text, (info_x, 20))
    my_username_text = small_font.render(my_username, True, BLACK)
    screen.blit(my_username_text, (info_x, 50))
    my_score_text = small_font.render(f"Очки: {my_score}", True, BLACK)
    screen.blit(my_score_text, (info_x, 80))

    # Колонка с информацией о противнике
    opponent_info_text = small_font.render(f"Противник:", True, BLACK)
    screen.blit(opponent_info_text, (info_x + 100, 20))
    opponent_username_text = small_font.render(opponent_username, True, BLACK)
    screen.blit(opponent_username_text, (info_x + 100, 50))
    opponent_score_text = small_font.render(f"Очки: {opponent_score}", True, BLACK)
    screen.blit(opponent_score_text, (info_x + 100, 80))

    # Отображение текущего хода
    turn_font = pygame.font.Font(None, 24)
    turn_text = "Ваша очередь хода" if my_turn else "Ожидаем ход противника"
    turn_color = RED if my_turn else BLACK
    turn_text_surface = turn_font.render(turn_text, True, turn_color)
    screen.blit(turn_text_surface, (info_x, 140))

    # Отображение таймера, если это ваш ход
    if my_turn and not endgame:
        time_left = 25 - int(time.time() - turn_start_time)
        if time_left <= 0:
            data = json.dumps(
                {'user_id': user_id,
                 'operation': 3, 'room_number': room_number}
            )
            client_socket.send(data.encode())
            while True:
                step_response = client_socket.recv(1024)
                if step_response:
                    step_response_data = json.loads(step_response)
                    winner_username = step_response_data.get('winner_username')
                    end_game(winner_username)
                    time_left = 0
                    break
        timer_text = small_font.render(f"Осталось: {time_left}s", True, BLACK)
        screen.blit(timer_text, (info_x, 180))

    # Отображение победителя
    if endgame:
        winner_text = font.render(f"Победитель: {winner_username}", True, BLACK)
        screen.blit(winner_text, (info_x, 240))

def end_game(winner):
    global endgame, winner_username
    endgame = True
    winner_username = winner

if __name__ == "__main__":
    main()

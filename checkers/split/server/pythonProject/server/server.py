import json
import os
import socket
import sqlite3
import threading
import select
from collections import defaultdict

CELL_SIZE = 80  # размер одной клетки в пикселях
BOARD_SIZE = 8  # размер доски 8x8
player_number = 0
rooms = defaultdict(list)  # Используем defaultdict для хранения комнат


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    create_connection(server_socket)

    while True:
        connection, client_address = server_socket.accept()
        try:
            data = connection.recv(1024).decode()
            if data:
                data_json = json.loads(data)
                if 'command' in data_json:
                    if data_json['command'] == 1:
                        threading.Thread(target=authorization, args=(connection, data_json)).start()
                    elif data_json['command'] == 2:
                        threading.Thread(target=register, args=(connection, data_json)).start()
                    elif data_json['command'] == 3:
                        threading.Thread(target=top_players, args=(connection, data_json)).start()
                    elif data_json['command'] == 4:
                        player_number = 1
                        room_number = len(rooms) + 1
                        user_id = data_json.get('user_id')
                        rooms[room_number] = [(player_number, connection, user_id)]  # Добавляем игрока номер 1
                        response_data = json.dumps({
                            'client_number': player_number,
                            'room_number': room_number
                        }).encode()
                        connection.sendall(response_data)
                    elif data_json['command'] == 5:
                        threading.Thread(target=show_rooms, args=(connection, rooms)).start()
                    elif data_json['command'] == 6:
                        user_id = data_json.get('user_id')
                        room_number = data_json.get('room_number')
                        threading.Thread(target=join_room, args=(connection, user_id, room_number)).start()
                    else:
                        print("Неверная команда!")
                else:
                    user_id = data_json.get('user_id')
                    # Поиск существующей комнаты с одним игроком
                    room_number = None
                    for rn, players in rooms.items():
                        if len(players) == 1:
                            room_number = rn
                            break

                    # Если такой комнаты нет, создаем новую
                    if room_number is None:
                        room_number = len(rooms) + 1
                        player_number = 1
                        rooms[room_number] = [(player_number, connection, user_id)]
                        print(f"Создана новая комната {room_number} и игрок {player_number} добавлен")
                    else:
                        player_number = 2
                        rooms[room_number].append((player_number, connection, user_id))
                        print(f"Игрок {player_number} добавлен в существующую комнату {room_number}")

                    response_data = json.dumps({
                        'client_number': player_number,
                        'room_number': room_number
                    }).encode()
                    connection.sendall(response_data)

                    if len(rooms[room_number]) == 2:
                        players = rooms[room_number]  # Получаем список игроков в комнате
                        start_game_message_send = json.dumps({
                            'message_start': "RdyCheck",
                            'players': [
                                {
                                    'player_number': p[0],
                                    'username': get_username_by_id(p[2]),
                                    'score': get_score_by_id(p[2]),
                                    'opponent_username': get_username_by_id(
                                        rooms[room_number][0 if p[0] == 2 else 1][2]),
                                    'opponent_score': get_score_by_id(rooms[room_number][0 if p[0] == 2 else 1][2])
                                } for p in players
                            ]
                        }).encode()
                        for _, conn, _ in players:
                            conn.sendall(start_game_message_send)
                        threading.Thread(target=handle_room, args=(players,)).start()
            else:
                print("Данных не получено, закрытие соединения")
                connection.close()
        except Exception as e:
            print(f"Ошибка при обработке подключения: {e}")
            connection.close()

def create_connection(server_socket):
    server_address = ('localhost', 43000)
    server_socket.bind(server_address)
    server_socket.listen(2)
    print('Сервер запущен, ожидаем подключения...')

def authorization(connection, data_json):
    try:
        username = data_json.get('username')
        password = data_json.get('password')

        if username is None or password is None:
            response = json.dumps({'status': False, 'message': 'Missing required fields'})
            connection.sendall(response.encode())
            return

        conn = sqlite3.connect(database_file)
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username=? AND password=?', (username, password))
        result = c.fetchone()
        conn.close()
        if result:
            user_id = result[0]
            response = json.dumps({'status': True, 'user_id': user_id})
        else:
            response = json.dumps({'status': False, 'message': 'Invalid username or password'})
        connection.sendall(response.encode())
    except Exception as e:
        print(f"Ошибка при обработке данных от клиента: {e}")
        connection.sendall(json.dumps({'status': 'error', 'message': 'Server error'}).encode())
    finally:
        connection.close()
def register(connection, data_json):
    try:
        username = data_json.get('username')
        password = data_json.get('password')

        if username is None or password is None:
            response = json.dumps({'status': False, 'message': 'Missing required fields'})
            connection.sendall(response.encode())
            return

        conn = sqlite3.connect(database_file)
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username=?', (username,))
        result = c.fetchone()

        if result:
            response = json.dumps({'status': False, 'message': 'Username already exists'})
        else:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            user_id = c.lastrowid
            response = json.dumps({'status': True, 'user_id': user_id})
        conn.close()

        connection.sendall(response.encode())
    except Exception as e:
        print(f"Ошибка при обработке данных от клиента: {e}")
        connection.sendall(json.dumps({'status': 'error', 'message': 'Server error'}).encode())
    finally:
        connection.close()
def top_players(connection, data_json):
    try:
        conn = sqlite3.connect(database_file)
        c = conn.cursor()

        # Выполнение запроса для получения первых 50 игроков по очкам в порядке убывания
        query = """
        SELECT username, score
        FROM users
        ORDER BY score DESC
        LIMIT 50
        """
        c.execute(query)
        top_players = c.fetchall()

        result = []
        for i, (username, score) in enumerate(top_players, start=1):
            result.append(f"{i}: {username}: {score} очков")

        if result:
            response = json.dumps({'status': True, 'message': result})
        else:
            response = json.dumps({'status': False, 'message': "Error"})

        c.close()
        conn.close()

        connection.sendall(response.encode())

    except Exception as e:
        print(f"Ошибка при обработке данных от клиента: {e}")
        connection.sendall(json.dumps({'status': 'error', 'message': 'Server error'}).encode())
    finally:
        connection.close()

def handle_room(players):
    connections = [p[1] for p in players]  # Получаем список соединений из списка игроков
    ready_status = {}  # Словарь для отслеживания статуса готовности игроков
    while True:
        readable, _, exceptional = select.select(connections, [], connections, None)
        for connection in readable:
            player_number = next((num for num, conn, _ in players if conn == connection), None)
            try:
                data = connection.recv(1024).decode()
                if data:
                    data_json = json.loads(data)
                    if 'status' in data_json:
                        ready_status[player_number] = data_json['status']
                        print(f"Игрок {player_number} статус готовности: {data_json['status']}")
                        if len(ready_status) == len(players) and all(status == True for status in ready_status.values()):
                            print("Оба игрока готовы, отправка сообщения StartGame")  # Отладочная информация
                            for conn in connections:
                                conn.sendall(json.dumps({"message_start": "StartGame"}).encode())
                    else:
                        operation = int(data_json['operation'])
                        if operation == 1:
                            client_number = int(data_json['client_number'])
                            row, col = data_json['row'], data_json['col']
                            pieces = data_json['pieces']
                            checkCell(connection, row, col, client_number, pieces)
                        elif operation == 2:
                            room_number = int(data_json['room_number'])
                            selected_piece = data_json['selected_piece']
                            client_number = int(data_json['client_number'])
                            row, col = data_json['row'], data_json['col']
                            pieces = data_json['pieces']
                            checkStep(row, col, client_number, pieces, selected_piece, room_number)
                        elif operation == 3:
                            user_id = (data_json['user_id'])
                            room_number = int(data_json['room_number'])
                            end_game(user_id, room_number)
                        else:
                            print("Неверная операция!")
            except ConnectionResetError:
                print(f"Игрок {player_number} отключился")
                connections.remove(connection)
                if not connections:
                    return
            except Exception as e:
                print(f"Ошибка при обработке данных: {e}")

        for connection in exceptional:
            player_number = next((num for num, conn, _ in players if conn == connection), None)
            print(f"Проблема с сокетом игрока {player_number}")
            connections.remove(connection)
            connection.close()
            if not connections:
                return

def calculate_possible_moves(pieces, row, col, client_number):
    opponent = 2 if client_number == 1 else 1
    moves = []
    # Добавляем все направления для возможности "съесть" шашку
    if client_number == 1:
        # Красные шашки двигаются вниз или "съедают" назад
        normal_moves = [(1, -1), (1, 1)]
        capture_moves = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    else:
        # Белые шашки двигаются вверх или "съедают" назад
        normal_moves = [(-1, -1), (-1, 1)]
        capture_moves = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    # Проверка обычного движения
    for d in normal_moves:
        new_row, new_col = row + d[0], col + d[1]
        if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and pieces[new_row][new_col] == 0:
            moves.append((new_row, new_col))

    # Проверка возможности "съесть" шашку
    for d in capture_moves:
        new_row, new_col = row + d[0], col + d[1]
        if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and pieces[new_row][new_col] == opponent:
            jump_row, jump_col = new_row + d[0], new_col + d[1]
            if 0 <= jump_row < BOARD_SIZE and 0 <= jump_col < BOARD_SIZE and pieces[jump_row][jump_col] == 0:
                moves.append((jump_row, jump_col))
    return moves

def has_possible_moves(pieces, client_number):
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if pieces[row][col] == client_number:
                moves = calculate_possible_moves(pieces, row, col, client_number)
                if moves:
                    return True
    return False

def make_move(pieces, row, col, selected_piece, client_number):
    pieces[selected_piece[0]][selected_piece[1]] = 0

    captured = False
    if abs(row - selected_piece[0]) == 2 and abs(col - selected_piece[1]) == 2:
        middle_row = (selected_piece[0] + row) // 2
        middle_col = (selected_piece[1] + col) // 2
        pieces[middle_row][middle_col] = 0
        captured = True

    pieces[row][col] = int(client_number)

    if captured and check_continuous_capture(pieces, row, col, client_number):
        return pieces, True, 0  # Можем продолжить ход

    # Проверка на победу
    if not any(1 in row for row in pieces):
        return pieces, False, 2  # Победил игрок 2
    elif not any(2 in row for row in pieces):
        return pieces, False, 1  # Победил игрок 1

    # Проверка на наличие одного камня и отсутствие возможных ходов
    if sum(row.count(client_number) for row in pieces) == 1 and not has_possible_moves(pieces, client_number):
        return pieces, False, 2 if client_number == 1 else 1  # Побеждает противник

    return pieces, False, 0  # Ход завершен, игра продолжается

def check_continuous_capture(pieces, row, col, client_number):
    opponent = 2 if client_number == 1 else 1
    capture_moves = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    for d in capture_moves:
        new_row, new_col = row + d[0], col + d[1]
        if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE and pieces[new_row][new_col] == opponent:
            jump_row, jump_col = new_row + d[0], new_col + d[1]
            if 0 <= jump_row < BOARD_SIZE and 0 <= jump_col < BOARD_SIZE and pieces[jump_row][jump_col] == 0:
                return True
    return False

def checkCell(connection, row, col, client_number, pieces):
    if pieces[row][col] == client_number:  # Проверяем, принадлежит ли фишка игроку
        selected_item = (int(row), int(col))
        response = json.dumps({'selected_item': selected_item})
        connection.sendall(response.encode())
        acknowledgment = connection.recv(1024).decode()
        if acknowledgment == "Received":
            possibles = calculate_possible_moves(pieces, int(row), int(col), int(client_number))
            data_to_send = json.dumps({'possible_moves': possibles})  # Сериализуем список ходов в JSON
            connection.sendall(data_to_send.encode())  # Отправляем JSON строку, закодированную в байты
    else:
        response_data = {
            'selected_item': None
        }
        response = json.dumps(response_data)
        connection.sendall(response.encode())

def checkStep(row, col, client_number, pieces, selected_piece, room_number):
    global rooms
    first_client_connection = None
    second_client_connection = None
    first_client_id = None
    second_client_id = None
    for player, conn, user_id in rooms[room_number]:
        if player == 1:
            first_client_connection = conn
            first_client_id = user_id
        else:
            second_client_connection = conn
            second_client_id = user_id

    winner_username = ""
    loser_username = ""
    pieces, can_continue, game_status = make_move(pieces, row, col, selected_piece, client_number)
    if game_status in [1, 2]:
        winner_id = first_client_id if game_status == 1 else second_client_id
        loser_id = second_client_id if game_status == 1 else first_client_id
        winner_username = get_username_by_id(winner_id)
        loser_username = get_username_by_id(loser_id)
        update_scores(winner_id, loser_id)
        delete_room(room_number)

    step_response = json.dumps({
        'pieces': pieces,
        'continue_step': can_continue,
        'game_status': game_status,
        'winner_username': winner_username,
        'loser_username': loser_username
    })
    if first_client_connection:
        first_client_connection.sendall(step_response.encode())
    opponent_step = json.dumps({
        'pieces': pieces,
        'continue_step': can_continue,
        'game_status': game_status,
        'winner_username': winner_username,
        'loser_username': loser_username
    })
    if second_client_connection:
        second_client_connection.sendall(opponent_step.encode())

def end_game(user_id_client, room_number):
    global rooms
    first_client_connection = None
    second_client_connection = None
    second_user_id = None
    first_client_number = None
    for player, conn, user_id in rooms[room_number]:
        if user_id == user_id_client:
            first_client_connection = conn
            first_client_number = player
        else:
            second_client_connection = conn
            second_user_id = user_id

    update_scores(second_user_id, user_id_client)
    winner_username = get_username_by_id(second_user_id)
    step_response = json.dumps({
        'winner_username': winner_username,
    })
    game_status = None
    if first_client_number == 1:
        game_status = 2
    elif first_client_number == 2:
        game_status = 1
    else:
        print("game_status не определён!")
        return
    if first_client_connection:
        first_client_connection.sendall(step_response.encode())
    opponent_step = json.dumps({
        'winner_username': winner_username,
        'game_status': game_status
    })
    if second_client_connection:
        second_client_connection.sendall(opponent_step.encode())
    delete_room(room_number)


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
database_path = os.path.join(base_dir, 'database')
database_file = os.path.join(database_path, 'users.db')

def get_username_by_id(user_id):
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_score_by_id(user_id):
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    c.execute('SELECT score FROM users WHERE id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_scores(winner_id, loser_id):
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    c.execute('UPDATE users SET score = score + 25 WHERE id = ?', (winner_id,))
    c.execute('UPDATE users SET score = score - 25 WHERE id = ?', (loser_id,))
    conn.commit()
    conn.close()

def show_rooms(connection, rooms):
    try:
        conn = sqlite3.connect(database_file)
        cursor = conn.cursor()

        result = []
        for room_id, players in rooms.items():
            creator_id = players[0][2] if players else 'Unknown'  # Предполагается, что игрок номер 1 - создатель комнаты
            cursor.execute("SELECT username FROM users WHERE id = ?", (creator_id,))
            creator_nickname = cursor.fetchone()
            creator_nickname = creator_nickname[0] if creator_nickname else 'Unknown'
            player_count = len(players)
            result.append({
                'room_id': room_id,
                'creator': creator_nickname,
                'player_count': player_count
            })

        response = json.dumps({'status': True, 'message': result})
        connection.sendall(response.encode())

    except Exception as e:
        print(f"Ошибка при обработке данных от клиента: {e}")
        connection.sendall(json.dumps({'status': 'error', 'message': 'Server error'}).encode())
    finally:
        connection.close()
        if conn:
            conn.close()

def delete_room(room_number):
    global rooms
    if room_number in rooms:
        del rooms[room_number]


def join_room(connection, user_id, room_number):
    global rooms
    if room_number in rooms:
        players = rooms[room_number]
        if len(players) < 2:
            player_number = 2
            rooms[room_number].append((player_number, connection, user_id))
            print(f"Игрок {player_number} добавлен в комнату {room_number}")

            response_data = json.dumps({
                'client_number': player_number,
                'room_number': room_number
            }).encode()
            connection.sendall(response_data)

            # Проверяем, заполнена ли комната
            if len(rooms[room_number]) == 2:
                players = rooms[room_number]
                start_game_message_send = json.dumps({
                    'message_start': "RdyCheck",
                    'players': [
                        {
                            'player_number': p[0],
                            'username': get_username_by_id(p[2]),
                            'score': get_score_by_id(p[2]),
                            'opponent_username': get_username_by_id(
                                rooms[room_number][0 if p[0] == 2 else 1][2]),
                            'opponent_score': get_score_by_id(rooms[room_number][0 if p[0] == 2 else 1][2])
                        } for p in players
                    ]
                }).encode()
                for _, conn, _ in players:
                    conn.sendall(start_game_message_send)
                threading.Thread(target=handle_room, args=(players,)).start()
        else:
            response = json.dumps({'status': False, 'message': 'Комната уже заполнена'})
            connection.sendall(response.encode())
            connection.close()
    else:
        response = json.dumps({'status': False, 'message': 'Комната не существует'})
        connection.sendall(response.encode())
        connection.close()


if __name__ == "__main__":
    main()

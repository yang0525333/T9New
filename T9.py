import asyncio
import requests
import websockets
import json
import datetime
import psycopg2
from psycopg2 import Error, pool

message_queue = asyncio.Queue()
db_pool = None
websocket_connection = None

async def init_db_pool():
    global db_pool
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            dbname="d5rambgu7d2n92",
            user="u75p3bjmps553l",
            password="p9a01ca7070c719e093cf202a51ac3bace95a2869fb77852052b8958e57b7ac16",
            host="ccba8a0vn4fb2p.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
            port="5432"
        )
        if db_pool:
            print("Connection pool created successfully")
    except Error as e:
        print(f"Error while connecting to PostgreSQL: {e}")

async def get_db_connection():
    try:
        return db_pool.getconn()
    except Error as e:
        print(f"Error getting connection from pool: {e}")

async def release_db_connection(conn):
    try:
        db_pool.putconn(conn)
    except Error as e:
        print(f"Error releasing connection back to pool: {e}")

async def Message_handler():
    while True:
        message = await message_queue.get()
        if message['OpCode'] == 'RoundResult':
            print(message)
            Table_id = message['TableId']
            banker_points = message['BankerPoints']
            player_points = message['PlayerPoints']
            banker_cards = json.dumps(message['BankerCard'])
            player_cards = json.dumps(message['PlayerCard'])
            win_area = message['WinArea']
            game_date = datetime.datetime.now()
            Player_Win = Banker_Win = Tie_Game = Any_Pair = Perfect_Pair = Lucky_Six = Player_Pair = Banker_Pair = False

            for Winner in win_area:
                if Winner == 0:
                    Banker_Win = True
                elif Winner == 1:
                    Player_Win = True
                elif Winner == 2:
                    Tie_Game = True
                elif Winner == 4:
                    Player_Pair = True
                elif Winner == 9:
                    Any_Pair = True
                elif Winner == 3:
                    Banker_Pair = True
                elif Winner in [6, 26]:
                    Lucky_Six = True
                elif Winner == 10:
                    Perfect_Pair = True

            conn = await get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO game_result (table_id, game_date, banker_points, player_points, banker_card, player_card, player_win, banker_win, tie_game, any_pair, perfect_pair, lucky_six, player_pair, banker_pair)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    ''', (Table_id, game_date, banker_points, player_points, banker_cards, player_cards, Player_Win, Banker_Win, Tie_Game, Any_Pair, Perfect_Pair, Lucky_Six, Player_Pair, Banker_Pair))
                    conn.commit()
                    print(f"RoundResult Table: {Table_id}")
                except Error as e:
                    print(f"Database error: {e}")
                finally:
                    await release_db_connection(conn)

        elif message['OpCode'] == 'Shuffle':
            Event_time = datetime.datetime.now()
            conn = await get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO event (event_type, table_id, event_time)
                        VALUES (%s, %s, %s)
                    ''', (message['OpCode'], message['TableId'], Event_time))
                    conn.commit()
                    print(f"Inserted Shuffle record into database for Table {message['TableId']}")
                except Error as e:
                    print(f"Database error: {e}")
                finally:
                    await release_db_connection(conn)
        message_queue.task_done()

async def LoginGetToken():
    url = 'https://g.t9cn818.online/api/Lobby/login'
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json; charset=UTF-8',
        'origin': 'https://g.t9cn818.online',
    }
    data = {
        "Language": "TW",
        "Account": "369p2",
        "Password": "aaa999",
        "SerialNumber": "ZRh51c2ONj",
        "Merchant": "_T9",
        "Device": "2"
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)
    print(response.json())
    return response.json()

async def EnterTable(websocket, login_data):
    LoginTable = login_data['Data']['GameList'][0]['TableList'][0]['TableId']
    EnterTable_data = {
        "OpCode": "EnterTable",
        "Data": {
            "GameType": "80001",
            "TableId": LoginTable,
            "EnterTableInLobby": "true"
        },
        "Token": login_data['Data']['Token']
    }
    print(EnterTable_data)
    await websocket.send(json.dumps(EnterTable_data))

async def Synctime(websocket, login_data):
    SynctimeBody = {
        "OpCode": "SyncTime",
        "Data": {
            "GameType": "80001"
        },
        "Token": login_data['Data']['Token']
    }
    await websocket.send(json.dumps(SynctimeBody))

async def periodic_sync(websocket, login_data, interval=5):
    while True:
        try:
            await asyncio.sleep(interval)
            await Synctime(websocket, login_data)
        except Exception as e:
            print(f'Synctime Exception error: {e}')

async def connect():
    global websocket_connection
    if websocket_connection:
        await websocket_connection.close()  # 如果已有連線，先關閉

    try:
        login_data = await LoginGetToken()
        websocketURL = login_data['Data']['ConnectIds'][0]
        url = f'wss://g.t9cn818.online/api/baccarat{websocketURL}'
        print(url)

        headers = {
            'Origin': 'https://g.t9cn818.online',
            'Host': 'g.t9cn818.online'
        }

        websocket_connection = await websockets.connect(url, extra_headers=headers)
        auth_data = {
            "OpCode": "LoginGame",
            "Data": {
                "AgentId": "19414",
                "MemberName": "386p2",
                "AccountType": "1",
                "Password": "aaa999",
                "GameType": "80001",
                "GetBroadCast": "1"
            },
            "Token": login_data['Data']['Token']
        }
        await websocket_connection.send(json.dumps(auth_data))
        print(auth_data)

        await asyncio.gather(
            periodic_sync(websocket_connection, login_data),  
            receive_messages(websocket_connection, login_data)
        )

    except websockets.ConnectionClosed:
        print("WebSocket connection closed.")

    except Exception as e:
        print(f"Error: {str(e)}")

async def receive_messages(websocket, login_data):
    while True:
        message = await websocket.recv()
        try:
            message_data = json.loads(message)
            if message_data['OpCode'] == 'DisConnected':
                print("WebSocket disconnected.")
                break 

            elif message_data['OpCode'] == 'LoginGame':
                print("Enter Table Message")
                await EnterTable(websocket=websocket, login_data=login_data)
            elif message_data['OpCode'] == 'RoundResult' or message_data['OpCode'] == 'Shuffle':
                await message_queue.put(message_data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except KeyError as e:
            print(f"KeyError: {e}. Message: {message}")
        except Exception as e:
            print(f"Unexpected error: {e}")

async def main():
    try:
        await init_db_pool()
        await asyncio.gather(
            connect(),
            Message_handler()
        )
    except Exception as e:
        print(f"Exception in main: {e}")

async def restart_worker_after(interval):
    while True:
        await asyncio.sleep(interval)
        print("Restarting worker...")
        asyncio.create_task(main())

async def start():
    main_task = asyncio.create_task(main())
    restart_task = asyncio.create_task(restart_worker_after(interval=1800))
    await main_task 
    await restart_task  

if __name__ == "__main__":
    asyncio.run(start())

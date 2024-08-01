import asyncio , traceback , gc
import requests
import websockets
import json
from datetime import datetime, timedelta 
import psycopg2
from psycopg2 import Error, pool


message_queue = asyncio.Queue()
db_pool = None
websocket_connection = None
login_data = None
main_task = None
Checksynctime = 0

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
    finally:
        gc.collect()

async def Message_handler():
    global websocket_connection , db_pool , login_data , Checksynctime
    while True:
        try :
            if websocket_connection.open :
                message = await message_queue.get()
                if message['OpCode'] == 'RoundResult':
                    Checksynctime = 0
                    print(message)
                    Table_id = message['TableId']
                    banker_points = message['BankerPoints']
                    player_points = message['PlayerPoints']
                    banker_cards = json.dumps(message['BankerCard'])
                    player_cards = json.dumps(message['PlayerCard'])
                    win_area = message['WinArea']
                    game_date = datetime.now()
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
                            for Card in message['BankerCard']:
                                if Card != 0 :
                                    query = f'''
                                        UPDATE poker_record
                                        SET "{Card}" = "{Card}" - 1
                                        WHERE tableid = {Table_id}
                                        AND shuffle_time = (
                                            SELECT MAX(shuffle_time)
                                            FROM poker_record
                                            WHERE tableid = {Table_id}
                                        )
                                    '''
                                    cursor.execute(query)
                            for Card in message['PlayerCard']:
                                if Card != 0 :
                                    query = f'''
                                        UPDATE poker_record
                                        SET "{Card}" = "{Card}" - 1
                                        WHERE tableid = {Table_id}
                                        AND shuffle_time = (
                                            SELECT MAX(shuffle_time)
                                            FROM poker_record
                                            WHERE tableid = {Table_id}
                                        )
                                    '''
                                    cursor.execute(query)
                            conn.commit()
                            print(f"RoundResult Table: {Table_id}")
                        except Error as e:
                            print(f"Database error: {e}")
                        finally:
                            await release_db_connection(conn)

                elif message['OpCode'] == 'Shuffle':
                    Event_time = datetime.now()
                    conn = await get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO event (event_type, table_id, event_time)
                                VALUES (%s, %s, %s)
                            ''', (message['OpCode'], message['TableId'], Event_time))
                            cursor.execute('''
                                INSERT INTO poker_record (TableId, Shuffle_time)
                                VALUES (%s, %s)
                            ''', (message['TableId'], Event_time))
                            conn.commit()
                            print(f"Inserted Shuffle record into database for Table {message['TableId']}")
                        except Error as e:
                            print(f"Database error: {e}")
                        finally:
                            await release_db_connection(conn)
                elif message['OpCode'] == 'DisConnected':
                    print("Message websocket connect close.")
                    db_pool = None
                    login_data = None
                    websocket_connection = None
                    break
                message_queue.task_done()
            else :
                print("Message websocket connect close.")
                db_pool = None
                login_data = None
                websocket_connection = None
                break
        except Exception as e:
            print(f"Message handling error: {e}")
            break
        except :
            print("Message break")
            break
            
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

async def EnterTable(websocket):
    global login_data , websocket_connection
    print(login_data)
    try :
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
    except:
        print("login failed")
        await asyncio.sleep(30)
        await websocket_connection.close()
        websocket_connection = None

async def Synctime():
    global websocket_connection, login_data , db_pool , Checksynctime
    SynctimeBody = {
        "OpCode": "SyncTime",
        "Data": {
            "GameType": "80001"
        },
        "Token": login_data['Data']['Token']
    }
    try:
        if websocket_connection.open:
            await websocket_connection.send(json.dumps(SynctimeBody))
            Checksynctime += 1
            print(f"Send synctime success. {Checksynctime}")
            if Checksynctime > 11 :
                print("No roundresult message over eight time , loop break 30 s")
                await asyncio.sleep(30)
                Checksynctime = 0
                await websocket_connection.close()
                websocket_connection = None
                login_data = None
                db_pool = None
                return True
        else:
            print("WebSocket connection is not open.")
            websocket_connection = None
            db_pool = None
            login_data = None
            return True
    except websockets.ConnectionClosed as e:
        print(f"WebSocket connection closed unexpectedly: {e}")
    except Exception as e:
        print(f"Error sending SyncTime message: {e}")
        websocket_connection = None
        db_pool = None
        login_data = None
        return True

async def periodic_sync(interval=5):
    global websocket_connection , login_data , db_pool
    while True:
        try:
            await asyncio.sleep(interval)
            connectclose = await Synctime()
            if connectclose == True:
                print("periodic_sync break")
                break
        except Exception as e:
            print("periodic_sync break")
            break

async def connect():
    global websocket_connection, login_data , db_pool
    if websocket_connection and websocket_connection.open:
        print("Closing previous WebSocket connection...")
        await websocket_connection.close()
        print(websocket_connection)
    try:
        login_data = await LoginGetToken()
        websocketURL = login_data['Data']['ConnectIds'][0]
        url = f'wss://p.t9live3.vip/api/baccarat{websocketURL}'
        print(url)

        headers = {
            'Origin': 'https://g.t9cn818.online',
            'Host': 'g.t9cn818.online'
        }
        websocket_connection = await websockets.connect(url, extra_headers=headers)
        print(websocket_connection)
        print("-----------------Connected to WebSocket.-----------------")
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

    except websockets.ConnectionClosed:
        print("WebSocket connection closed.")

    except Exception as e:
        print(f"Error: {str(e)}")

async def receive_messages():
    global websocket_connection, login_data, db_pool
    while True:
        try :
            if websocket_connection.open:
                message = await websocket_connection.recv()
                try:
                    message_data = json.loads(message)
                    if message_data['OpCode'] == 'DisConnected':
                        await message_queue.put(message_data)
                        print("WebSocket disconnected.")
                        websocket_connection = None
                        login_data = None
                        db_pool = None
                        break
                    elif message_data['OpCode'] == 'LoginGame':
                        print("Enter Table Message")
                        await EnterTable(websocket=websocket_connection)
                    elif message_data['OpCode'] == 'RoundResult' or message_data['OpCode'] == 'Shuffle':
                        await message_queue.put(message_data)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                except KeyError as e:
                    print(f"KeyError: {e}. Message: {message}")
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    traceback.print_exc()  
            else:
                login_data = None
                db_pool = None
                websocket_connection = None
                DisconnectMessage = {
                    "OpCode" : "DisConnected"
                }
                await message_queue.put(DisconnectMessage)
                print("Receive message break")
                break
        except :
            login_data = None
            db_pool = None
            websocket_connection = None
            DisconnectMessage = {
                "OpCode" : "DisConnected"
            }
            await message_queue.put(DisconnectMessage)
            print("Receive message break")
            break

async def fetch_data(start_time,end_time):
    try :
        conn = await get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                table_id,
                COUNT(CASE WHEN player_win THEN 1 END) AS player_win_count,
                COUNT(CASE WHEN banker_win THEN 1 END) AS banker_win_count,
                COUNT(CASE WHEN tie_game THEN 1 END) AS tie_game_count,
                COUNT(CASE WHEN any_pair THEN 1 END) AS any_pair_count,
                COUNT(CASE WHEN perfect_pair THEN 1 END) AS perfect_pair_count,
                COUNT(CASE WHEN lucky_six THEN 1 END) AS lucky_six_count,
                COUNT(CASE WHEN player_pair THEN 1 END) AS player_pair_count,
                COUNT(CASE WHEN banker_pair THEN 1 END) AS banker_pair_count
            FROM 
                game_result
            WHERE 
                game_date BETWEEN %s AND %s
            GROUP BY 
                table_id;
        ''', (start_time, end_time))

        data = cursor.fetchall()
        conn.close()
        sum_player_win = sum(data[i][1] for i in range(len(data)))
        sum_banker_win = sum(data[i][2] for i in range(len(data)))
        sum_tie_game = sum(data[i][3] for i in range(len(data)))
        sum_any_pair = sum(data[i][4] for i in range(len(data)))
        sum_perfect_pair = sum(data[i][5] for i in range(len(data)))
        sum_lucky_six = sum(data[i][6] for i in range(len(data)))
        sum_player_pair = sum(data[i][7] for i in range(len(data)))
        sum_banker_pair = sum(data[i][8] for i in range(len(data)))
        total = (0,sum_player_win,sum_banker_win,sum_tie_game,sum_any_pair,sum_perfect_pair,sum_lucky_six,sum_player_pair,sum_banker_pair)
        data.insert(0 ,(total))
        await release_db_connection(conn)
        return data
    except :
        print("fetch data error")

async def LineNotify(message):
    own = 'geIsbH0HS5wIVG2vYO8mr207ZwRyhqgtRGtBAZkWQV4'
    line_notify_token = 'bzc2iwQg5XyFjDcyitfAVkBc7fwapNDvKxUlzx2E7bO'
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': f'Bearer {line_notify_token}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'message': message
    }
    response = requests.post(line_notify_api, headers=headers, data=data)
    if response.status_code == 200:
        print('Notification sent successfully!')
    else:
        print(f'Failed to send notification: {response.status_code}')

async def CheckProbability():
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=int(5))
        data = await fetch_data(start_time = start_time,end_time = end_time)
        print(data)
        TotalPlayer = data[0][1]
        TotalBanker = data[0][2]
        TotalTie = data[0][3]
        TotalAnypair = data[0][4]
        TotalPerfectpair = data[0][5]
        TotalLuckySix = data[0][6]
        TotalPlayerpair = data[0][7]
        TotalBankerpair = data[0][8]
        TotleGameRound = TotalPlayer + TotalBanker + TotalTie
        PlayerProbability = (TotalPlayer / TotleGameRound) * 100
        BankerProbability = (TotalBanker / TotleGameRound) * 100
        TieProbability = (TotalTie / TotleGameRound) * 100
        AnypairProbability = (TotalAnypair / TotleGameRound) * 100
        PerfectpairProbability = (TotalPerfectpair / TotleGameRound) * 100
        LuckySixProbability = (TotalLuckySix / TotleGameRound) * 100
        PlayerpairProbability = (TotalPlayerpair / TotleGameRound) * 100
        BankerpairProbability = (TotalBankerpair / TotleGameRound) * 100
        if PlayerpairProbability < 2 :
            message = f'近5分鐘內每桌總和後"閒對"勝率僅剩{round(PlayerpairProbability, 2)}% , https://t9live-b5c2cbf5b1b9.herokuapp.com/'
            await LineNotify(message)
        if BankerpairProbability < 2 :
            message = f'近5分鐘內每桌總和後"莊對"家勝率僅剩{round(BankerpairProbability, 2)}% , https://t9live-b5c2cbf5b1b9.herokuapp.com/'
            await LineNotify(message)
        conn = await get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (fetch_time, player, banker ,tie , any_pair, perfect_pair, lucky_six, player_pair, banker_pair)
            VALUES (%s, %s, %s ,%s ,%s, %s, %s, %s, %s)
        ''', (end_time + timedelta(hours=8) , PlayerProbability , BankerProbability , TieProbability , AnypairProbability , PerfectpairProbability , LuckySixProbability , PlayerpairProbability , BankerpairProbability))
        conn.commit()
        await release_db_connection(conn)
    except Exception as e:
        print(f"Fetch data error {e}")

async def CheckProbabilityWorker(interval=5):
    while True:
        try:
            i = 0
            while i < 12 :
                if websocket_connection.open :
                    await asyncio.sleep(interval)
                    i += 1
                else :
                    print("CheckProbabilityWorker break")
                    break
            if websocket_connection.open :
                await CheckProbability()
            else :
                print("CheckProbabilityWorker break")
                break
        except Exception as e:
            print("CheckProbabilityWorker break")
            break
        
    
async def main():
    try:
        await init_db_pool()
        await connect()
        await asyncio.gather(
            Message_handler(),
            periodic_sync(),
            receive_messages(),
            CheckProbabilityWorker()
        )
    except Exception as e:
        print("Main loop restart")
        return
    

async def start():
    global login_data , db_pool , websocket_connection
    while True:
        try:
            login_data = None
            db_pool = None
            websocket_connection = None
            gc.collect()
            print("gc.collect()")
            await main()
        except Exception as e:
            print("-------------Restart-------------")
            print(f"Error starting application: {e}")

if __name__ == "__main__":
    asyncio.run(start())

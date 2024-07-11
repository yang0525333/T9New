import requests
import asyncio
import websockets
import base64
import json
import os
import sqlite3
import datetime

async def DB_connect():
    DATABASE_PATH = 'T9.db'
    conn = sqlite3.connect(DATABASE_PATH)
    conn.commit()
    return conn

async def Message_handler (conn , message):
    if message['OpCode'] == 'RoundResult':
        table_id = message['TableId']
        banker_points = message['BankerPoints']
        player_points = message['PlayerPoints']
        banker_cards = json.dumps(message['BankerCard'])
        player_cards = json.dumps(message['PlayerCard'])
        win_area = message['WinArea']
        game_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        Player_Win = 0
        Banker_Win = 0
        Tie_Game = 0
        Any_Pair = 0
        Perfect_Pair = 0
        Lucky_Six = 0
        Player_Pair = 0
        Banker_Pair = 0
        for Winner in win_area :
            if Winner == 0 :
                Banker_Win = 1
            elif Winner == 1 :
                Player_Win = 1 
            elif Winner == 2 :
                Tie_Game = 1
            elif Winner == 4 :
                Player_Pair = 1 
            elif Winner == 9 :
                Any_Pair = 1 
            elif Winner == 3 :
                Banker_Pair = 1
            elif Winner == 6 or Winner == 26:
                Lucky_Six = 1
            elif Winner == 10 :
                Perfect_Pair = 1 
        cursor = conn.cursor()
        cursor.execute('''
                INSERT INTO Game_Result (table_id, game_date, Banker_Points, Player_Points, Banker_Card, Player_Card, Player_Win,Banker_Win,Tie_Game,Any_Pair,Perfect_Pair,Lucky_Six,Player_Pair,Banker_Pair)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (table_id, game_date, banker_points, player_points, banker_cards, player_cards, Player_Win, Banker_Win, Tie_Game, Any_Pair, Perfect_Pair, Lucky_Six, Player_Pair, Banker_Pair))
        conn.commit()
    elif message['OpCode'] == 'Shuffle' :
        Event_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        cursor.execute('''
                INSERT INTO Event (Event_type , Table_id , Event_time)
                VALUES (?, ?, ?)
            ''', (message['OpCode'] , message['TableId']), Event_time)
        conn.commit()

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
        "Account": "km831yt",
        "Password": "ken456xyz1",
        "SerialNumber": "qhqEgHivcW",
        "Merchant": "_T9",
        "Device": "2"
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)
    print(response.json())
    return response.json()

async def EnterTable(websocket, login_data):
    EnterTable_data = {
        "OpCode": "EnterTable",
        "Data": {
            "GameType": "80001",
            "TableId": "99",
            "EnterTableInLobby": "true"
        },
        "Token": login_data['Data']['Token']
    }
    await websocket.send(json.dumps(EnterTable_data))

async def connect():
    while True:  # Outer loop for reconnecting
        try:
            login_data = await LoginGetToken()
            conn = await DB_connect()
            websocketURL = login_data['Data']['ConnectIds'][0]
            url = f'wss://g.t9cn818.online/api/baccarat{websocketURL}'
            print(url)

            headers = {
                'Origin': 'https://g.t9cn818.online',
                'Host': 'g.t9cn818.online'
            }

            async with websockets.connect(url, extra_headers=headers) as websocket:
                if websocket:
                    auth_data = {
                        "OpCode": "LoginGame",
                        "Data": {
                            "AgentId": "17619",
                            "MemberName": "km831yt",
                            "AccountType": "1",
                            "Password": "ken456xyz1",
                            "GameType": "80001",
                            "GetBroadCast": "1"
                        },
                        "Token": login_data['Data']['Token']
                    }
                    await websocket.send(json.dumps(auth_data))
                    print(auth_data)

                    while True:  # Inner loop for receiving messages
                        message = await websocket.recv()
                        try:
                            message_data = json.loads(message)
                            if message_data['OpCode'] == 'DisConnected':
                                print("WebSocket disconnected.")
                                break  # Exit the inner loop and reconnect

                            elif message_data['OpCode'] == 'LoginGame':
                                print("Enter Table Message")
                                await EnterTable(websocket=websocket, login_data=login_data)
                            elif message_data['OpCode'] == 'RoundResult' or message_data['OpCode'] == 'StartGame' or message_data['OpCode'] == 'Shuffle':
                                await Message_handler(conn=conn , message=message_data)
                                print(message_data)

                        except :
                            print("Receive message error")

        except websockets.ConnectionClosed:
            conn.close()
            print("WebSocket connection closed, retrying immediately...")

        except Exception as e:
            print(f"Error: {str(e)}")
            print("Retrying immediately...")

asyncio.get_event_loop().run_until_complete(connect())

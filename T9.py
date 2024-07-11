import requests
import asyncio
import websockets
import base64
import json
import os
import sqlite3

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
                            elif message_data['OpCode'] == 'RoundResult':
                                print(message_data)
                            elif message_data['OpCode'] == 'StartGame':
                                print(message_data)
                            elif message_data['OpCode'] == 'Shuffle':
                                print(message_data)
                        except :
                            print("Receive message error")

        except websockets.ConnectionClosed:
            print("WebSocket connection closed, retrying immediately...")

        except Exception as e:
            print(f"Error: {str(e)}")
            print("Retrying immediately...")

asyncio.get_event_loop().run_until_complete(connect())

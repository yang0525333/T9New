import requests 
from datetime import datetime, timedelta
import psycopg2

DB_NAME = "d5rambgu7d2n92"
DB_USER = "u75p3bjmps553l"
DB_PASSWORD = "p9a01ca7070c719e093cf202a51ac3bace95a2869fb77852052b8958e57b7ac16"
DB_HOST = "ccba8a0vn4fb2p.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"

def db_connect():
    conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
    )
    return conn

def fetch_data(start_time,end_time):
    conn = db_connect()
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
    return data

def LineNotify(message):
    own = 'geIsbH0HS5wIVG2vYO8mr207ZwRyhqgtRGtBAZkWQV4'
    line_notify_token = 'bzc2iwQg5XyFjDcyitfAVkBc7fwapNDvKxUlzx2E7bO'
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': f'Bearer {own}'
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
        end_time = datetime.now() - timedelta(hours=8)
        start_time = end_time - timedelta(hours=int(1))
        data = fetch_data(start_time = start_time,end_time = end_time)
        print(data)
        TotalPlayer = data[0][1]
        TotalBanker = data[0][2]
        TotleTie = data[0][3]
        TotleGameRound = TotalPlayer + TotalBanker + TotleTie
        PlayerProbability = (TotalPlayer / TotleGameRound) * 100
        BankerProbability = (TotalBanker / TotleGameRound) * 100
        TieProbability = (TotleTie / TotleGameRound) * 100
        if PlayerProbability > 49  :
            message = '近一小時內每桌總和後閒家勝率 > 49%'
            LineNotify(message)
        if BankerProbability < 49 :
            message = '近一小時內每桌總和後莊家家勝率 > 49%'
            LineNotify(message)
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (fetch_time, player, banker ,tie)
            VALUES (%s, %s, %s ,%s)
        ''', (end_time , PlayerProbability , BankerProbability , TieProbability))
        conn.commit()
        conn.close()

    except Exception as e:
        print(f'Error during API call: {e}')
        return False
    
from flask import Flask, render_template, request, jsonify
import psycopg2
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import requests

app = Flask(__name__)

# Database connection details (replace with your own)
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

def calculate_time_range(time_amount, time_unit):
    if time_unit == 'hour':
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=int(time_amount))
    elif time_unit == 'day':
        end_time = datetime.now()
        start_time = end_time - timedelta(days=int(time_amount))
    else:
        raise ValueError("Invalid time unit")
    return start_time, end_time

@app.route('/', methods=['GET', 'POST'])
def search_data():
    time_amount = None
    time_unit = None

    if request.method == 'POST':
        if 'quick_search' in request.form:
            if 'time_amount' in request.form and 'time_unit' in request.form:
                time_amount = request.form['time_amount']
                time_unit = request.form['time_unit']
                start_time, end_time = calculate_time_range(time_amount, time_unit)
            else:
                start_time = datetime.now() - timedelta(days=1)  # Default to 1 day ago
                end_time = datetime.now()
        else:
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            if isinstance(start_time, str):
                try:
                    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
                start_time -= timedelta(hours=8) 

            if isinstance(end_time, str):
                try:
                    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
                end_time -= timedelta(hours=8) 

        print(start_time)
        print(end_time)

        try:
            data = fetch_data(start_time=start_time,end_time=end_time)
            print(data)

            start_time = (start_time + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            end_time = (end_time + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            
            return render_template('search_data.html', data=data, show_results=True, start_time=start_time, end_time=end_time, time_amount=time_amount, time_unit=time_unit)

        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            return "Error connecting to database."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "An unexpected error occurred."

    return render_template('search_data.html', show_results=False)

@app.route('/get_table_details', methods=['POST'])
def get_table_details():
    table_id = request.json.get('table_id')
    print(table_id)
    try:
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT event_time
            FROM (
                SELECT event_time, 
                    ROW_NUMBER() OVER (ORDER BY event_time DESC) AS row_num
                FROM event
                WHERE table_id = %s AND event_type = 'Shuffle'
            ) AS subquery
            WHERE row_num <= 2
            ORDER BY event_time DESC;
        ''', (table_id,))

        results = cursor.fetchall()
        last_shuffle_time = results[0][0] if len(results) > 0 else None
        second_last_shuffle_time = results[1][0] if len(results) > 1 else None
        print(last_shuffle_time)
        if last_shuffle_time:
            cursor.execute('''
                SELECT 
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
                    table_id = %s AND game_date BETWEEN %s AND %s
            ''', (table_id, last_shuffle_time , datetime.now()))
            game_results = cursor.fetchall()
        else:
            game_results = []
        if second_last_shuffle_time:
            cursor.execute('''
                SELECT 
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
                    table_id = %s AND game_date BETWEEN %s AND %s
            ''', (table_id, second_last_shuffle_time , last_shuffle_time))
            game_results2 = cursor.fetchall()
        else:
            game_results = []
        conn.close()
        if last_shuffle_time:
            last_shuffle_time = (last_shuffle_time + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        if second_last_shuffle_time:
            second_last_shuffle_time = (second_last_shuffle_time + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'last_shuffle_time': last_shuffle_time,
            'second_last_shuffle_time' : second_last_shuffle_time,
            'game_results': game_results,
            'game_results2' : game_results2
        })

    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return jsonify({'error': 'Error connecting to database.'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500
    
@app.route("/new_search", methods=["GET", "POST"])
def new_search():
    start_time = None
    end_time = None
    new_search_results = []

    if request.method == 'POST':
        if 'quick_search' in request.form:
            if 'time_amount' in request.form and 'time_unit' in request.form:
                time_amount = request.form['time_amount']
                time_unit = request.form['time_unit']
                start_time, end_time = calculate_time_range(time_amount, time_unit)
                start_time += timedelta(hours=8)
                end_time += timedelta(hours=8)
            else:
                start_time = datetime.now() - timedelta(days=1) 
                end_time = datetime.now()
        else:
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            if isinstance(start_time, str):
                try:
                    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
                

            if isinstance(end_time, str):
                try:
                    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
                

        print(start_time)
        print(end_time)

        try:
            conn = db_connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    fetch_time,
                    player,
                    banker,
                    tie,
                    any_pair,
                    perfect_pair,
                    lucky_six,
                    player_pair,
                    banker_pair
                FROM history
                WHERE fetch_time BETWEEN %s AND %s
            ''', (start_time, end_time))
            raw_results = cursor.fetchall()
            
            # Format the results
            new_search_results = []
            for row in raw_results:
                fetch_time = row[0].strftime('%Y-%m-%d %H:%M:%S')  # Format to second
                player_prob = f"{row[1]:.2f}%"
                banker_prob = f"{row[2]:.2f}%"
                tie_prob = f"{row[3]:.2f}%"
                any_pair_prob = f"{row[4]:.2f}%"
                perfect_pair_prob = f"{row[5]:.2f}%"
                lucky_six_prob = f"{row[6]:.2f}%"
                player_pair_prob = f"{row[7]:.2f}%"
                banker_pair_prob = f"{row[8]:.2f}%"
                new_search_results.append((fetch_time, player_prob, banker_prob, tie_prob, any_pair_prob, perfect_pair_prob, lucky_six_prob, player_pair_prob, banker_pair_prob))
            new_search_results.sort(key=lambda x: x[0], reverse=True)
                
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template("new_search.html", show_new_search_results=True, new_search_results=new_search_results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8888)))

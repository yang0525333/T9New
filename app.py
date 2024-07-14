from flask import Flask, render_template, request
import psycopg2
from datetime import datetime, timedelta

app = Flask(__name__)

# Database connection details (replace with your own)
DB_NAME = "d5rambgu7d2n92"
DB_USER = "u75p3bjmps553l"
DB_PASSWORD = "p9a01ca7070c719e093cf202a51ac3bace95a2869fb77852052b8958e57b7ac16"
DB_HOST = "ccba8a0vn4fb2p.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"

from datetime import datetime, timedelta

def calculate_time_range(time_amount, time_unit):
    if time_unit == 'hour':
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=int(time_amount))
    elif time_unit == 'day':
        end_time = datetime.now()
        start_time = end_time - timedelta(days=int(time_amount))
    else:
        raise ValueError("Invalid time unit")

    # Format datetime objects as strings
    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

    return start_time_str, end_time_str


@app.route('/', methods=['GET', 'POST'])
def search_data():
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
            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

        try:
            print(f"start_time : {start_time}")
            print(f"end_time : {end_time}")
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )

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

            return render_template('search_data.html', data=data, show_results=True, start_time=start_time, end_time=end_time)

        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            return "Error connecting to database."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "An unexpected error occurred."

    return render_template('search_data.html', show_results=False)

if __name__ == '__main__':
    app.run(debug=True)

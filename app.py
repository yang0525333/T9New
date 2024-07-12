from flask import Flask, jsonify, request, render_template
import sqlite3
import T9

app = Flask(__name__)

# 資料庫路徑
DATABASE_PATH = 'T9.db'

# 簡單的根路徑路由，返回一個包含選擇時間表單的 HTML 頁面
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# HTTP POST 請求的路由，用於根據選擇的時間範圍檢索資料
@app.route('/search', methods=['POST'])
def search_data():
    try:
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * WHERE Table_id = 100 FROM Game_Result WHERE Game_date BETWEEN ? AND ?", (start_time, end_time))
        data = cursor.fetchall()
        conn.close()
        
        return render_template('result.html', data=data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)

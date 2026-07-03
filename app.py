from flask import Flask, render_template_string, request
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('practice_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

# 秒数を「〇時間 〇分 〇秒」の文字列に変換するヘルパー関数
def format_seconds(total_seconds):
    if not total_seconds:
        return "0秒"
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    result = ""
    if hours > 0:
        result += f"{hours}時間 "
    if minutes > 0 or hours > 0:
        result += f"{minutes}分 "
    result += f"{seconds}秒"
    
    return result

# --- 画面1: ログイン・登録画面のHTML ---
AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>継続練習を目指すアプリ - 認証</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-100 flex flex-col items-center justify-center min-h-screen p-4">
    <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 class="text-2xl font-bold mb-6 text-center text-gray-800">継続練習アプリ</h1>
        
        {% if error_message %}<div class="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded text-sm">{{ error_message }}</div>{% endif %}
        {% if success_message %}<div class="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded text-sm">{{ success_message }}</div>{% endif %}

        <div class="mb-8">
            <h2 class="text-lg font-semibold mb-3 text-gray-700">ログイン</h2>
            <form action="/login" method="POST" class="space-y-3">
                <div>
                    <label class="block text-sm text-gray-600">メールアドレス</label>
                    <input type="text" name="email" class="mt-1 block w-full rounded border border-gray-300 p-2" required>
                </div>
                <div>
                    <label class="block text-sm text-gray-600">パスワード</label>
                    <input type="password" name="password" class="mt-1 block w-full rounded border border-gray-300 p-2" required>
                </div>
                <button type="submit" class="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">ログイン</button>
            </form>
        </div>
        <hr class="border-gray-200 mb-6">
        <div>
            <h2 class="text-lg font-semibold mb-3 text-gray-700">アカウント新規登録</h2>
            <form action="/register" method="POST" class="space-y-3">
                <div>
                    <label class="block text-sm text-gray-600">メールアドレス</label>
                    <input type="text" name="email" class="mt-1 block w-full rounded border border-gray-300 p-2" required>
                </div>
                <div>
                    <label class="block text-sm text-gray-600">パスワード</label>
                    <input type="password" name="password" class="mt-1 block w-full rounded border border-gray-300 p-2" required>
                </div>
                <button type="submit" class="w-full bg-green-500 text-white p-2 rounded hover:bg-green-600">新規登録</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# --- 画面2: マイページ（履歴＆総時間一覧）のHTML ---
MYPAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>継続練習を目指すアプリ - マイページ</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-100 min-h-screen p-6">
    <div class="max-w-md mx-auto bg-white p-8 rounded-lg shadow-md">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-xl font-bold text-gray-800">マイページ</h1>
            <a href="/" class="text-sm text-red-500 hover:underline">ログアウト</a>
        </div>
        <p class="text-sm text-gray-500 mb-6">ようこそ、{{ email }} さん</p>

        <div class="bg-blue-50 border border-blue-200 p-4 rounded-lg text-center mb-6">
            <h2 class="text-xs font-bold text-blue-700 uppercase tracking-wide">🔥 これまでの総練習時間</h2>
            <p class="text-2xl font-black text-blue-900 mt-1" id="totalTimeDisplay">{{ total_time_str }}</p>
        </div>

        <form action="/timer" method="POST" class="mb-8">
            <input type="hidden" name="user_id" value="{{ user_id }}">
            <input type="hidden" name="email" value="{{ email }}">
            <button type="submit" class="w-full bg-blue-500 text-white p-3 rounded-lg font-bold shadow hover:bg-blue-600 transition">
                ⏱️ 新しい練習タイマーを起動する
            </button>
        </form>

        <div class="border-t pt-4">
            <h2 class="text-md font-bold text-gray-700 mb-3">これまでの練習記録</h2>
            {% if sessions %}
                <ul class="space-y-2">
                {% for s in sessions %}
                    <li class="bg-gray-50 p-3 rounded border border-gray-200 flex justify-between text-sm">
                        <span class="font-mono text-gray-600">{{ s.practice_date }}</span>
                        <span class="font-bold text-blue-600">{{ s.duration_seconds }} 秒</span>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p class="text-sm text-gray-400 text-center py-4">まだ記録がありません。タイマーで測ってみましょう！</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# --- 画面3: タイマー・記録画面のHTML ---
TIMER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>継続練習を目指すアプリ - タイマー</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-100 min-h-screen p-6">
    <div class="max-w-md mx-auto bg-white p-8 rounded-lg shadow-md text-center">
        <div class="text-left mb-4">
            <form action="/login" method="POST">
                <input type="hidden" name="email" value="{{ email }}">
                <input type="hidden" name="bypass_password" value="true">
                <button type="submit" class="text-sm text-blue-500 hover:underline">← マイページに戻る</button>
            </form>
        </div>
        
        <h1 class="text-xl font-bold text-gray-800 mb-2">練習タイマー</h1>
        <p class="text-sm text-gray-500 mb-6">計測中: {{ email }}</p>

        <div class="text-5xl font-mono font-bold text-blue-600 my-8" id="timerDisplay">00:00:00</div>

        <div class="flex justify-center space-x-4 mb-8">
            <button id="startBtn" onclick="startTimer()" class="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600">スタート</button>
            <button id="pauseBtn" onclick="pauseTimer()" class="bg-yellow-500 text-white px-6 py-2 rounded hover:bg-yellow-600 hidden">一時停止</button>
            <button id="startBtn2" onclick="startTimer()" class="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 hidden">再開</button>
            <button id="stopBtn" onclick="stopTimer()" class="bg-red-500 text-white px-6 py-2 rounded hover:bg-red-600 hidden">ストップ</button>
        </div>

        <form action="/save_session" method="POST" id="saveForm" class="hidden border-t pt-6 space-y-4 text-left">
            <input type="hidden" name="user_id" value="{{ user_id }}">
            <input type="hidden" name="email" value="{{ email }}">
            <input type="hidden" name="duration" id="durationInput">

            <div>
                <label class="block text-sm font-medium text-gray-700">計測結果（秒）</label>
                <input type="text" id="durationDisplay" class="mt-1 block w-full bg-gray-100 border p-2 rounded" readonly>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">練習日（自動記録）</label>
                <input type="text" name="date" value="{{ today }}" class="mt-1 block w-full bg-gray-100 border p-2 rounded" readonly>
            </div>
            
            <button type="submit" class="w-full bg-green-500 text-white p-3 rounded font-bold hover:bg-green-600">
                この内容で練習を記録する
            </button>
        </form>
    </div>

    <script>
        let timer = null;
        let seconds = 0;

        function updateDisplay() {
            let hrs = Math.floor(seconds / 3600).toString().padStart(2, '0');
            let mins = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
            let secs = (seconds % 60).toString().padStart(2, '0');
            document.getElementById('timerDisplay').innerText = `${hrs}:${mins}:${secs}`;
        }

        function startTimer() {
            if (timer === null) {
                timer = setInterval(() => { seconds++; updateDisplay(); }, 1000);
                document.getElementById('startBtn').classList.add('hidden');
                document.getElementById('startBtn2').classList.add('hidden');
                document.getElementById('pauseBtn').classList.remove('hidden');
                document.getElementById('stopBtn').classList.remove('hidden');
            }
        }

        function pauseTimer() {
            clearInterval(timer);
            timer = null;
            document.getElementById('startBtn2').classList.remove('hidden');
            document.getElementById('pauseBtn').classList.add('hidden');
        }

        function stopTimer() {
            clearInterval(timer);
            timer = null;
            if (seconds === 0) {
                alert("練習時間が0秒のため、記録できません。");
                location.reload();
                return;
            }
            document.getElementById('durationInput').value = seconds;
            document.getElementById('durationDisplay').value = seconds + " 秒";
            document.getElementById('saveForm').classList.remove('hidden');
            document.getElementById('startBtn').classList.add('hidden');
            document.getElementById('startBtn2').classList.add('hidden');
            document.getElementById('pauseBtn').classList.add('hidden');
            document.getElementById('stopBtn').classList.add('hidden');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(AUTH_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    if not email or not password or "@" not in email:
        return render_template_string(AUTH_TEMPLATE, error_message="登録内容が正しくありません。")
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template_string(AUTH_TEMPLATE, error_message="既に登録されているメールアドレスです。")
    finally:
        conn.close()
    return render_template_string(AUTH_TEMPLATE, success_message="登録完了！ログインしてください。")

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    bypass = request.form.get('bypass_password')

    conn = get_db_connection()
    
    if bypass == "true":
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    else:
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()

    if user is None:
        conn.close()
        return render_template_string(AUTH_TEMPLATE, error_message="ログインに失敗しました。")

    # 過去の練習記録を取得
    sessions = conn.execute('SELECT * FROM practice_sessions WHERE user_id = ? ORDER BY session_id DESC', (user['user_id'],)).fetchall()
    
    # 🆕 データベースから総練習時間（秒数）を計算して取得する
    total_row = conn.execute('SELECT SUM(duration_seconds) as total FROM practice_sessions WHERE user_id = ?', (user['user_id'],)).fetchone()
    total_seconds = total_row['total'] if total_row['total'] is not None else 0
    
    # 🆕 ヘルパー関数で「〇時間〇分〇秒」に変換
    total_time_str = format_seconds(total_seconds)
    
    conn.close()

    # 総時間の文字列も一緒にテンプレートへ渡す
    return render_template_string(MYPAGE_TEMPLATE, email=user['email'], user_id=user['user_id'], sessions=sessions, total_time_str=total_time_str)

@app.route('/timer', methods=['POST'])
def timer():
    user_id = request.form.get('user_id')
    email = request.form.get('email')
    today_str = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(TIMER_TEMPLATE, email=email, user_id=user_id, today=today_str)

@app.route('/save_session', methods=['POST'])
def save_session():
    user_id = request.form.get('user_id')
    email = request.form.get('email')
    duration = request.form.get('duration')
    date_str = request.form.get('date')

    if not duration or int(duration) <= 0:
        return "エラー: 計測時間が不正です。", 400

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO practice_sessions (user_id, practice_date, duration_seconds) 
        VALUES (?, ?, ?)
    ''', (user_id, date_str, int(duration)))
    conn.commit()
    
    # マイページ再表示用のデータ取得
    sessions = conn.execute('SELECT * FROM practice_sessions WHERE user_id = ? ORDER BY session_id DESC', (user_id,)).fetchall()
    
    # 🆕 保存完了時にも総練習時間を再計算して反映させる
    total_row = conn.execute('SELECT SUM(duration_seconds) as total FROM practice_sessions WHERE user_id = ?', (user_id,)).fetchone()
    total_seconds = total_row['total'] if total_row['total'] is not None else 0
    total_time_str = format_seconds(total_seconds)
    
    conn.close()

    return render_template_string(MYPAGE_TEMPLATE, email=email, user_id=user_id, sessions=sessions, total_time_str=total_time_str)

if __name__ == '__main__':
    app.run(debug=True)
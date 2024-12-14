from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
# load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# MySQL使用のフラグ（Falseにするとモックを使用）
USE_MYSQL = False

# モックデータ用リスト
mock_chat_history = []

# MySQL database connection function
def get_db_connection():
    if not USE_MYSQL:
        print("MySQL connection skipped (using mock data).")
        return None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),        # MySQLホスト名
            user=os.getenv("MYSQL_USER"),        # MySQLユーザー名
            password=os.getenv("MYSQL_PASSWORD"),# MySQLパスワード
            database=os.getenv("MYSQL_DB")       # MySQLデータベース名
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise

# Initialize database
def init_db():
    if USE_MYSQL:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    conversation_json TEXT,
                    family_score INT,
                    hobby_score INT,
                    work_score INT,
                    health_score INT,
                    money_score INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()
            cursor.close()
            conn.close()
            print("Database initialized successfully.")
        except Error as e:
            print(f"Error initializing the database: {e}")
            raise
    else:
        print("Database initialization skipped (using mock data).")

# Save chat history to the database or mock
def save_chat_history(user_id, conversation_json, scores):
    if USE_MYSQL:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history (user_id, conversation_json, family_score, hobby_score, 
                                          work_score, health_score, money_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, conversation_json, scores['family_score'], scores['hobby_score'], 
                  scores['work_score'], scores['health_score'], scores['money_score']))
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            print(f"Error saving to MySQL: {e}")
    else:
        # Save to mock data
        mock_chat_history.append({
            "user_id": user_id,
            "conversation_json": conversation_json,
            "scores": scores
        })
        print(f"Mock save: {mock_chat_history[-1]}")

@app.route('/')
def index():
    return "Welcome to the LasTomo App!"

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    message = data.get('message')
    history = data.get('history', [])

    # Prepare conversation context
    messages = [
        {"role": "system", "content": """あなたは終活コンサルタントです。
        ユーザーの終活に関する以下の5つの観点を評価してください：
        1. 家族関係
        2. 趣味・生きがい
        3. 仕事・キャリア
        4. 健康・医療
        5. 経済状況
        
        自然な会話を通じてユーザーの状況を理解し、適切なアドバイスを提供してください。
        会話が10往復程度進んだら、これまでの会話を元に上記5項目について5段階評価を行い、
        その理由と今後のアドバイスを提供してください。"""}
    ]
    
    # Add conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current message
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Save chat history (mock or MySQL)
        save_chat_history(
            user_id=1,
            conversation_json=str(history),
            scores={"family_score": 5, "hobby_score": 4, "work_score": 3, 
                    "health_score": 4, "money_score": 2}
        )
        
        return jsonify({"response": ai_response})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "Failed to get response from AI"}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8000)


from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# MySQL使用のフラグ（Falseにするとモックを使用）
USE_MYSQL = True

# モックデータ用リスト
mock_chat_history = []

# MySQL database connection function
def get_db_connection():
    if not USE_MYSQL:
        print("MySQL connection skipped (using mock data).")
        return None
    try:
        print("connecting to MySQL")
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

            # プロフィールデータ用テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255),
                    nickname VARCHAR(255),
                    email VARCHAR(255),
                    gender VARCHAR(50),
                    age INT,
                    occupation VARCHAR(255),
                    family_structure VARCHAR(255),
                    location VARCHAR(255),
                    nationality VARCHAR(255),
                    religion VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')            
            
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

# Save profile data to the database
@app.route('/api/save-profile', methods=['POST'])
def save_profile():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_profiles (
                    username, nickname, email, gender, age, occupation, 
                    family_structure, location, nationality, religion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('username'), data.get('nickname'), data.get('email'),
                data.get('gender'), int(data.get('age')), data.get('occupation'),
                data.get('familyStructure'), data.get('location'),
                data.get('nationality'), data.get('religion')
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "プロフィールが正常に保存されました！"}), 200
        else:
            return jsonify({"error": "データベース接続に失敗しました"}), 500
    except Error as e:
        print(f"Error saving profile to MySQL: {e}")
        return jsonify({"error": "プロフィールの保存に失敗しました"}), 500

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
        その理由と今後のアドバイスを提供してください。また可読性を上げるために、その理由と今後のアドバイスは項目ごとに改行した形で提供ください"""}
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

@app.route('/api/values', methods=['GET'])
def get_values_data():
    if USE_MYSQL:  # MySQLが有効な場合
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute('''
                    SELECT family_score, hobby_score, work_score, health_score, money_score
                    FROM chat_history
                    ORDER BY created_at DESC
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                if result:
                    return jsonify({"scores": [
                        result["family_score"],
                        result["hobby_score"],
                        result["work_score"],
                        result["health_score"],
                        result["money_score"],
                    ]})
                else:
                    return jsonify({"error": "No data found"}), 404
        except Error as e:
            print(f"Error fetching data from MySQL: {e}")
            return jsonify({"error": "Database error"}), 500
    # モックデータを返す
    values_data = {
        "scores": [4, 3, 5, 4, 2]  # モックデータ
    }
    return jsonify(values_data)

@app.route('/api/action-plan', methods=['GET'])
def generate_action_plan():
    try:
        # MySQL から個人データとリフレクションログを取得
        profile, chat_history = None, None
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # 個人データ取得
            cursor.execute('SELECT * FROM user_profiles ORDER BY created_at DESC LIMIT 1')
            profile = cursor.fetchone()

            # リフレクションログ取得
            cursor.execute('SELECT conversation_json FROM chat_history ORDER BY created_at DESC LIMIT 1')
            chat_history = cursor.fetchone()

            cursor.close()
            conn.close()

        # MySQL のデータが不足している場合
        if not profile or not chat_history:
            print("MySQLからのデータ取得に失敗。モックデータを使用します。")
            profile = {
                "username": "サンプル太郎",
                "nickname": "タロ",
                "email": "sample@example.com",
                "gender": "男性",
                "age": 31,
                "occupation": "メーカーの研究職",
                "family_structure": "妻と子供1人",
                "location": "栃木県",
                "nationality": "日本",
                "religion": "無宗教"
            }
            chat_history = {
                "conversation_json": """[
                    {"role": "user", "content": "最近は忙しくて、クタクタです"},
                    {"role": "assistant", "content": "それは大変そうですね。お身体には十分気をつけてください。もしよければ、その忙しさの原因は何でしょうか？ 仕事でしょうか、それとも何か別のことでしょうか？"}
                    {"role": "user", "content": "仕事も忙しいですが、子供生まれて、育児もあるのが大変です。私は核家族で、両親も遠いので、私と妻で切り盛りしなくといけないので"},
                    {"role": "assistant", "content": "お子様が生まれて、それは新たな喜びと役割が増えたのですね。おめでとうございます！そして、それは確かに大変だと思います。一方で、お仕事についてもお話しいただけますか？何をされているのか、またはそれがどのくらいの時間を占めているのかなど。"}
                    {"role": "user", "content": "私はメーカーの研究開発職です。実験をしたり、資料を作ったり、部下のマネジメントをしたり、学会発表をしたりさまざまなことをしています。"},
                    {"role": "assistant", "content": "それは多岐に渡るお仕事のようですね。ご自身の能力を活かしていて素晴らしいと思います。育児と仕事が忙しい中、自分自身の時間を作ることはできていますか？趣味や楽しみについて何かありますか？？"}
                    {"role": "user", "content": "自分の時間はほとんどないですね。仕事と育児でほぼ時間がありません。"},
                    {"role": "assistant", "content": "それは大変な状況ですね。自分の時間がないと、ストレスが溜まりがちです。また、健康や医療についてはどうですか？ 定期的に健康診断を受けていますか？また、何か特別な健康上の課題はありますか？"}
                    {"role": "user", "content": "実は数年前にがんになりました。今は寛かいしており、通院などはしておりません。ただ疲労が取れないのが悩みです"},
                    {"role": "それは大変な経験をされたのですね。がんを寛解されているとのこと、それは本当に良かったです。一方、疲労が取れないとのことは気になりますね。お身体のことは何より大切ですから、可能であれば医療機関でのチェックをお勧めします。最後に、経済状況についてお伺いしたいのですが、節約や投資など、何か特別な取り組みをしていますか？"}
                    {"role": "user", "content": "NISAでインデックスファンドに投資をしています。ただ子供ができ、奥さんが育休になってからは、なかなか投資額の積み増しができておりません"},
                    {"role": "assistant", "content": "投資を行っているとのこと、将来に向けた計画があることは素晴らしいですね。しかし、現在の経済状況は厳しいようですね。それでは、これまでの会話を元に、5つの観点についての評価を行います。 1. **家族関係**：4/5 ご家族と一緒に子育てをされており、お互いのサポートがあるようです。しかし、親御さんが遠く、そのサポートは受けにくいとのこと。もし可能であれば、地域の子育て支援などを活用することをお勧めします。 2. **趣味・生きがい**：2/5 お仕事と子育てにより、自分自身の時間がほとんどないとのこと。ストレス発散や自己啓発のためにも、少しずつでも自分の時間を作ってみることをお勧めします。 3. **仕事・キャリア**：4/5 ご自身の職業については多岐にわたる業務をこなしており、能力を十分に発揮しているようです。ただし、時間が取れず、疲労がたまっているとのこと。仕事と生活のバランスを見直すことをお勧めします。 4. **健康・医療**：3/5 がんを寛解されていて、現在は特別な病気はないとのことですが、疲労が取れないとのこと。定期的な健康診断と、可能であれば疲労の原因を調べるための専門的な診断を受けることをお勧めします。 5. **経済状況**：3/5 投資により将来に備えているとのことですが、子育てのために投資額が積み増しできていないとのこと。家計全体の見直しや、必要であれば専門家の意見を聞くことをお勧めします。 これらの評価はあくまで一時点でのものです。状況が変われば、評価も変わることがあります。終活は一生続けるものですので、自分自身のライフスタイルを見直し、必要なところから改善していけば良いと思います。私たちはいつでもあなたの相談に応じますので、何かあれば遠慮なくお知らせください。"}                ]"""
            }

        # OpenAI へ送信するメッセージを作成
        system_prompt = """あなたは終活コンサルタントです。もらったチャットのログと個人データを参考にして、
        下記の4つの視点のなかから、少なくとも一つを終活のための具体的なアクションプランを提案してください。
        またそのアクションプランを実行するために参考になるWebページのURLを各視点から1つずつ上げなさい。
        また可読性を上げるために、1.2.3.4と順番に表記し、その視点ごとに改行した形で提供ください。
        ただし文字数は1000文字以内にしてください

        1:家族を含めた大切な人に残す遺産と相続先についての提案  
        2:自分が重大な病気になった時の治療(延命・臓器提供の有無)および介護についての提案  
        3:自分が亡くなった後の手続き(葬儀やお墓の希望、保険やデジタル遺産の解約)についての提案  
        4:あなたがこれから本当にやりたいことについての提案  
        """

        # ChatGPT へ送信するメッセージ
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"個人データ: {profile}\nリフレクションログ: {chat_history['conversation_json']}"}
        ]

        # OpenAI API の呼び出し
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        # ChatGPT の回答を取得
        action_plan = response.choices[0].message.content.strip()

        # 結果を返す
        return jsonify({"action_plan": action_plan}), 200

    except Exception as e:
        print(f"Error generating action plan: {e}")
        return jsonify({"error": "アクションプランの生成に失敗しました"}), 500


@app.route('/')
def index():
    return "Welcome to the Flask App!"

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)


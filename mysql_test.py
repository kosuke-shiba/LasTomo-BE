from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),        # MySQLホスト名
        user=os.getenv("MYSQL_USER"),        # MySQLユーザー名
        password=os.getenv("MYSQL_PASSWORD"),# MySQLパスワード
        database=os.getenv("MYSQL_DB")       # MySQLデータベース名
        #host="tech0-gen-8-step3-rdb-11.mysql.database.azure.com",
        #user="tech0gen8student",
        #password="5iTbVNuqQu8z11",
        #database="lastomo_db"
    )
    if conn.is_connected():
        print(conn.user)
        print(conn.database)
        print("MySQL接続成功！")
except mysql.connector.Error as e:
    print(f"エラー: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()

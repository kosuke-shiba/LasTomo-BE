import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="your_username",
        password="your_password"
    )
    if conn.is_connected():
        print("MySQL接続成功！")
except mysql.connector.Error as e:
    print(f"エラー: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()

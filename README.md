# Backend module for a web application "LasTomo".

1. Flask のセットアップ

1.1 仮想環境の作成と有効化
Python の仮想環境を作成します。

```bash
python -m venv venv
```

1.2仮想環境を有効化します。

macOS/Linuxの場合:
```bash
source venv/bin/activate
```
Windowsの場合:
```bash
venv\Scripts\activate
```

1.3 必要なパッケージのインストール

以下のコマンドを実行して Flask と Flask-CORS をインストールします。

```bash
pip install -r requirements.txt
```

1.4 app.pyの作成

app.py を記述します。
（既にファイルには記載済みです。）

1.5 以下のコマンドを実行して Flask サーバーを起動します。

```bash
python app.py
```

ブラウザで http://localhost:5000/ にアクセスして、{"message": "Welcome to the LasTomo App!"} が表示されることを確認します。

1.6 API（GET）の確認

ブラウザで http://localhost:5000/api/hello にアクセスして、{"message": "Hello World"} が表示されることを確認します。（未実装）

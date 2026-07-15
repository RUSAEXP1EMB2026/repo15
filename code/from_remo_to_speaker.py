"""
温度・湿度 音声読み上げシステム
出力先: TS-NS410W 内蔵スピーカー（Qwatch API経由）
使用ライブラリ: gTTS, requests
"""

import time
import random
import os
import tempfile
from gtts import gTTS
import requests
from requests.auth import HTTPDigestAuth


# ──────────────────────────────────────────
# カメラ設定
# ──────────────────────────────────────────

CAMERA_IP   = "192.168.1.2"       # カメラのIPアドレス
CAMERA_PORT = 80                   # HTTPポート番号
USERNAME    = "admin"              # 管理者ユーザー名
PASSWORD    = "your_password"      # パスワード

BASE_URL = f"http://{CAMERA_IP}:{CAMERA_PORT}"
AUTH     = HTTPDigestAuth(USERNAME, PASSWORD)


# ──────────────────────────────────────────
# データソース
# ──────────────────────────────────────────

import requests

ACCESS_TOKEN = "ここに取得したトークンを貼る"

def get_sensor_data() -> dict:
    response = requests.get(
        "https://api.nature.global/1/devices",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )
    device = response.json()[0]          # 1台目のデバイス
    temperature = device["newest_events"]["te"]["val"]  # 温度
    humidity    = device["newest_events"]["hu"]["val"]  # 湿度
    return {"temperature": temperature, "humidity": humidity}


# ──────────────────────────────────────────
# Qwatch API
# ──────────────────────────────────────────

def upload_audio(file_path: str, filename: str) -> bool:
    """音声ファイルをカメラにアップロードする。"""
    url = f"{BASE_URL}/camera-cgi/formuploadmusicfile.cgi"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "audio/mpeg")}
            resp = requests.post(url, auth=AUTH, files=files, timeout=15)
        if resp.status_code == 200 and "OK" in resp.text:
            print(f"  [API] アップロード成功: {filename}")
            return True
        else:
            print(f"  [API] アップロード失敗: {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  [API] 通信エラー（upload）: {e}")
        return False


def play_audio(filename: str) -> bool:
    """カメラ内の指定ファイルをスピーカーで再生する。"""
    url = f"{BASE_URL}/camera-cgi/admin/param.cgi"
    data = {
        "action":          "update",
        "Sound_playMusic": filename,
    }
    try:
        resp = requests.post(url, auth=AUTH, data=data, timeout=15)
        if resp.status_code == 200 and "OK" in resp.text:
            print(f"  [API] 再生開始: {filename}")
            return True
        else:
            print(f"  [API] 再生失敗: {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  [API] 通信エラー（play）: {e}")
        return False


def delete_audio(filename: str) -> None:
    """カメラ内の指定ファイルを削除する。"""
    url = f"{BASE_URL}/camera-cgi/admin/param.cgi"
    data = {
        "action":            "update",
        "Sound_deleteMusic": filename,
    }
    try:
        resp = requests.post(url, auth=AUTH, data=data, timeout=15)
        if resp.status_code == 200:
            print(f"  [API] ファイル削除: {filename}")
        else:
            print(f"  [API] 削除失敗: {resp.status_code} {resp.text}")
    except requests.RequestException as e:
        print(f"  [API] 通信エラー（delete）: {e}")


# ──────────────────────────────────────────
# 音声生成・送信
# ──────────────────────────────────────────

def announce_via_camera(message: str, playback_wait: float = 5.0) -> None:
    """
    テキストをgTTSで音声化し、カメラのスピーカーで再生する。

    Args:
        message:       読み上げるテキスト
        playback_wait: 再生完了を待つ時間（秒）。
                       ファイルの長さに応じて調整すること。
    """
    print(f"  [音声] {message}")

    # カメラ内でのファイル名（重複を避けるためタイムスタンプを付与）
    filename = f"announcement_{int(time.time())}.mp3"

    # 一時ファイルに音声を生成
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tts = gTTS(text=message, lang="ja")
        tts.save(tmp_path)

        # ① アップロード → ② 再生 → ③ 削除
        if upload_audio(tmp_path, filename):
            if play_audio(filename):
                # カメラ側の再生が終わるまで待機
                # ※ APIは再生完了を通知しないため time.sleep で代用
                time.sleep(playback_wait)
            delete_audio(filename)

    finally:
        # ローカルの一時ファイルを削除
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def announce_environment(data: dict) -> None:
    """取得したデータをアナウンス用テキストに変換して読み上げる。"""
    temp = data["temperature"]
    hum  = data["humidity"]
    message = f"現在の温度は{temp}度、湿度は{hum}パーセントです。"
    announce_via_camera(message, playback_wait=6.0)


# ──────────────────────────────────────────
# メインループ
# ──────────────────────────────────────────

def main():
    print("=" * 45)
    print("  温度・湿度 音声読み上げシステム 起動")
    print(f"  出力先: {CAMERA_IP}:{CAMERA_PORT}")
    print("=" * 45)
    print("Ctrl+C で終了\n")

    INTERVAL_SECONDS = 60  # 読み上げ間隔（秒）

    try:
        while True:
            data = get_sensor_data()
            print(f"[データ] 温度: {data['temperature']}℃  湿度: {data['humidity']}%")
            announce_environment(data)
            print(f"  → {INTERVAL_SECONDS}秒後に再取得します...\n")
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nシステムを終了します。")


if __name__ == "__main__":
    main()

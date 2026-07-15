"""
温度・湿度 音声読み上げシステム
使用ライブラリ: gTTS, pygame
"""

import time
import random
import os
import tempfile
from gtts import gTTS
import pygame


# ──────────────────────────────────────────
# データソース（ここを差し替えるだけでセンサー対応可能）
# ──────────────────────────────────────────

def get_sensor_data() -> dict:
    """
    温度・湿度を取得する関数。
    現在はダミーデータを返す。
    センサーに切り替える場合はここだけ修正すればOK。

    例（Raspberry Pi + DHT22）:
        import Adafruit_DHT
        humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, pin=4)
        return {"temperature": temperature, "humidity": humidity}
    """
    temperature = round(random.uniform(18.0, 35.0), 1)  # 18.0〜35.0℃
    humidity    = round(random.uniform(30.0, 80.0), 1)  # 30.0〜80.0%
    return {"temperature": temperature, "humidity": humidity}


# ──────────────────────────────────────────
# 音声生成・再生
# ──────────────────────────────────────────

def text_to_speech(text: str) -> None:
    """テキストを日本語音声に変換してスピーカーから再生する。"""
    print(f"[音声] {text}")

    # gTTSで音声データを生成
    tts = gTTS(text=text, lang="ja")

    # 一時ファイルに保存して再生
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tts.save(tmp_path)

        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        # 再生が終わるまで待機
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.music.unload()
        pygame.mixer.quit()

    finally:
        os.remove(tmp_path)


def announce_environment(data: dict) -> None:
    """取得したデータをアナウンス用テキストに変換して読み上げる。"""
    temp = data["temperature"]
    hum  = data["humidity"]
    message = f"現在の温度は{temp}度、湿度は{hum}パーセントです。"
    text_to_speech(message)


# ──────────────────────────────────────────
# メインループ
# ──────────────────────────────────────────

def main():
    print("=" * 45)
    print("  温度・湿度 音声読み上げシステム 起動")
    print("=" * 45)
    print("Ctrl+C で終了\n")

    INTERVAL_SECONDS = 10  # 読み上げ間隔（秒）

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

import io
import requests
from gtts import gTTS

# ==============================================================================
# 設定情報（カメラの接続情報）
# ==============================================================================
CAMERA_IP = "192.168.1.2"   # 👈 あなたのカメラのIPアドレスに変えてください
CAMERA_USER = "admin"       # 👈 カメラのログインユーザー名
CAMERA_PASS = "password"    # 👈 カメラのログインパスワード

# 仕様書に基づいた2つのエンドポイントURL
CAMERA_UPLOAD_URL = f"http://{CAMERA_IP}/form/formUploadMusicFile.cgi"
CAMERA_PLAY_URL = f"http://{CAMERA_IP}/camera-cgi/admin/param.cgi"

# 再生するファイルのインデックス番号（0 〜 19）
# ※アップロードしたファイルが何番に保存されるか、まずは「0」でテストします
MUSIC_INDEX = 0


def generate_speech_audio(temperature, humidity):
    """
    (機能1) 温度と湿度から文章を作り、その場で音声データ（MP3）に変換する
    """
    text = f"おかえりなさい。現在の室温は {temperature} 度、湿度は {humidity} パーセントです。"
    
    if temperature >= 28 and humidity >= 70:
        text += "少し蒸し暑くなっています。"
    elif temperature >= 25 and humidity >= 65:
        text += "ジメジメしているので、エアコンをつけたほうがいいかもしれません。"
    elif temperature <= 15:
        text += "お部屋が少し冷え込んでいます。"
        
    print(f"💬 作成したメッセージ: 「{text}」")
    
    tts = gTTS(text=text, lang='ja', slow=False)
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    
    return audio_buffer


def play_on_camera(audio_data):
    """
    (機能2) 仕様書に基づき、①アップロード ➔ ②再生 の2ステップを実行する
    """
    auth = (CAMERA_USER, CAMERA_PASS)
    
    # --------------------------------------------------------------------------
    # ステップ1: オーディオファイルのアップロード (formUploadMusicFile.cgi)
    # --------------------------------------------------------------------------
    print("📤 1/2: 音声ファイルをカメラにアップロード中...")
    
    # 仕様書の「form: fileToUpload」に基づき、キー名を fileToUpload に指定
    files = {
        "fileToUpload": ("speech.mp3", audio_data, "audio/mpeg")
    }
    
    try:
        # timeoutを設定してフリーズを防止
        upload_res = requests.post(CAMERA_UPLOAD_URL, files=files, auth=auth, timeout=10)
        upload_res.raise_for_status()
        print("✅ アップロードが成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"❌ アップロードに失敗しました: {e}")
        if 'upload_res' in locals():
            print(f"カメラからの応答: {upload_res.text}")
        return False

    # --------------------------------------------------------------------------
    # ステップ2: アップロードしたオーディオファイルの再生 (param.cgi)
    # --------------------------------------------------------------------------
    print(f"▶️ 2/2: インデックス番号 {MUSIC_INDEX} の再生を指示中...")
    
    # 仕様書の「action=MusicCtrl&MusicPlay=3」の形式に合わせる
    params = {
        "action": "MusicCtrl",
        "MusicPlay": str(MUSIC_INDEX)
    }
    
    try:
        # パラメータは URLクエリ（params）として送信します
        play_res = requests.post(CAMERA_PLAY_URL, params=params, auth=auth, timeout=10)
        play_res.raise_for_status()
        print("🎉 カメラのスピーカーから音声を再生しました！")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 再生指示に失敗しました: {e}")
        if 'play_res' in locals():
            print(f"カメラからの応答: {play_res.text}")
        return False


def execute_voice_notification(temperature, humidity):
    """
    (メイン機能) 温度と湿度を受け取り、音声作成からカメラでの再生までを一貫して行う
    """
    audio_data = generate_speech_audio(temperature, humidity)
    is_success = play_on_camera(audio_data)
    return is_success


# ==============================================================================
# テスト実行
# ==============================================================================
if __name__ == "__main__":
    print("--- Qwatch用 音声通知テスト ---")
    execute_voice_notification(28, 75)

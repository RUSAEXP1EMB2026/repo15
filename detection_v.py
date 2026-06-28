import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from requests.auth import HTTPDigestAuth
from datetime import datetime
import time

# --- 設定項目 ---
CAMERA_IP = "192.168.0.62" 
SENSOR_URL = f"http://{CAMERA_IP}/camera-cgi/com/sensor.cgi?start_time=now"
CAMERA_AUTH = ('admin', '20060829y') 
SHEET_NAME = "カメラ検知ログ"
JSON_KEYFILE = 'credentials.json'

# --- スプレッドシート接続 ---
print("スプレッドシートに接続しています...")
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

def get_sensor_status():
    try:
        res = requests.get(SENSOR_URL, auth=HTTPDigestAuth(*CAMERA_AUTH), timeout=10)
        res.raise_for_status()
        return res.json()["list"][0]
    except Exception:
        return None

def main():
    print("音量監視を開始しました（しきい値: 65）...")
    
    last_record_time = 0
    COOLDOWN_SECONDS = 30 # 連続記録を防ぐためのクールダウン時間

    while True:
        sensor_info = get_sensor_status()
        
        if sensor_info:
            # 取得した生データを表示
            print(f"現在値: {sensor_info}") 

            is_detected = False
            
            # --- 【検知条件の判定】 ---
            # 音量(volume)が65を超えたら検知とみなす
            try:
                volume = float(sensor_info.get("volume", 0))
                if volume > 65:
                    is_detected = True
            except (ValueError, TypeError):
                is_detected = False

            # --- 検知した時の処理 ---
            if is_detected:
                current_time = time.time()
                
                # クールダウン時間を超えている場合のみスプレッドシートに書き込み
                if (current_time - last_record_time) > COOLDOWN_SECONDS:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    row = [
                        now, 
                        sensor_info.get("temp", ""), 
                        sensor_info.get("humid", ""), 
                        sensor_info.get("volume", ""), 
                        sensor_info.get("bright", "")
                    ]
                    
                    try:
                        sheet.append_row(row)
                        print(f"🔥 音を検知しました！記録しました: {now}")#音量65を超えたら検知
                        last_record_time = current_time
                    except Exception as e:
                        print(f"書き込みエラー: {e}")
        
        # 2秒ごとに確認
        time.sleep(2)

if __name__ == "__main__":
    main()
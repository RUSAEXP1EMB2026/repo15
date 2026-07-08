"""
人感センサー検知（Gmail監視）→ Excel記録 + 音声読み上げシステム
使用ライブラリ: gTTS, pygame, requests, openpyxl, imaplib
"""

import time
import os
import tempfile
import imaplib
import email
import email.header
from datetime import datetime
from gtts import gTTS
import pygame
import requests
import openpyxl


# ──────────────────────F────────────────────
# Gmail設定
# ──────────────────────────────────────────

GMAIL_ADDRESS  = "ryo771166@gmail.com"
GMAIL_APP_PASS = "pwljhmweftvgqihl"

# ──────────────────────────────────────────
# LINE設定
# ──────────────────────────────────────────

LINE_ACCESS_TOKEN = "Nu06zHv7sivSMO9tkOhL8FaD/YkfMG5cdh5tKs1f+u1S1+vyfTm7bDQvBEducQhgmzYtFvmA6esuZBMMfwr+nAY/7UntUfmX/5i/f+n/YM3yi0Sjd2opKueDCSbBLQU8qw7cZG8UT3iQFMDabwN6ZgdB04t89/1O/w1cDnyilFU="
USER_ID = "U2b467b664b0d41f38f0e1129d26eef24"


# ──────────────────────────────────────────
# Excel設定
# ──────────────────────────────────────────

EXCEL_FILE       = "検知ログ.xlsx"
COOLDOWN_SECONDS = 15


# ──────────────────────────────────────────
# Nature Remo 温湿度取得
# ──────────────────────────────────────────

ACCESS_TOKEN = "ory_at_yKRB3nBsqzIBb49BecVG6yJ2kP2R7J_vfPTy9qsdEZk.DvcHE_PRzmJ3Icotnfhb9brVG8cnkRnPi6HKQo-r3JQ"

def get_temperature_humidity() -> dict:
    try:
        response = requests.get(
            "https://api.nature.global/1/devices",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            timeout=10
        )
        device = response.json()[0]
        temperature = device["newest_events"]["te"]["val"]
        humidity    = device["newest_events"]["hu"]["val"]
        return {"temperature": temperature, "humidity": humidity}
    except Exception as e:
        print(f"  [Remo] 取得エラー: {e}")
        return {"temperature": "--", "humidity": "--"}


# ──────────────────────────────────────────
# Excel書き込み
# ──────────────────────────────────────────

def write_to_excel(row: list) -> None:
    if os.path.exists(EXCEL_FILE):
        wb = openpyxl.load_workbook(EXCEL_FILE)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["日時", "温度(℃)", "湿度(%)"])
    ws.append(row)
    wb.save(EXCEL_FILE)
    print(f"  [Excel] 記録しました: {EXCEL_FILE}")


# ──────────────────────────────────────────
# Gmail接続
# ──────────────────────────────────────────

def connect_gmail() -> imaplib.IMAP4_SSL:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
    print("  [Gmail] 接続完了")
    return mail


# ──────────────────────────────────────────
# Gmail監視
# ──────────────────────────────────────────

def check_new_camera_mail(mail: imaplib.IMAP4_SSL, last_uid: str, last_date: str, start_time: datetime) -> tuple[bool, str, str]:
    try:
        mail.select("INBOX")

        # 起動日以降の未読メールのみ検索
        since_date = start_time.strftime("%d-%b-%Y")
        _, data = mail.search(None, f'(UNSEEN SINCE "{since_date}")')
        uids = data[0].split()

        if not uids:
            return False, last_uid, last_date

        latest_uid = uids[-1].decode()

        if latest_uid == last_uid:
            return False, last_uid, last_date

        _, msg_data = mail.fetch(latest_uid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        # 件名をデコード
        raw_subject = msg.get("Subject", "")
        decoded = email.header.decode_header(raw_subject)
        subject = ""
        for part, charset in decoded:
            if isinstance(part, bytes):
                charset = charset or "utf-8"
                if charset.lower() in ("unknown-8bit", "unknown"):
                    charset = "utf-8"
                subject += part.decode(charset, errors="ignore")
            else:
                subject += str(part)

        # 受信日時を取得
        mail_date = msg.get("Date", "")
        print(f"  [Gmail] 新着メール件名: {subject} ({mail_date})")

        # カメラ以外のメールはスキップ
        if "TS-NS410W" not in subject:
            print(f"  [Gmail] カメラ以外のメールのためスキップ")
            return False, latest_uid, last_date

        # 同じ日時のメールはスキップ
        if mail_date == last_date:
            print(f"  [Gmail] 同じ時刻のメールのためスキップ")
            return False, latest_uid, last_date

        return True, latest_uid, mail_date

    except Exception as e:
        print(f"  [Gmail] エラー: {e}")
        return False, last_uid, last_date

# ──────────────────────────────────────────
# LINE通知
# ──────────────────────────────────────────

def send_line(message: str) -> None:
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "to": USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            print("[LINE] 通知しました")
        else:
            print(f"[LINE] エラー: {response.text}")

    except Exception as e:
        print(f"[LINE] 送信エラー: {e}")
# ──────────────────────────────────────────
# 音声読み上げ（PCスピーカー）
# ──────────────────────────────────────────

def announce(message: str) -> None:
    print(f"  [音声] {message}")
    tts = gTTS(text=message, lang="ja")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tts.save(tmp_path)
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
        pygame.mixer.quit()
    finally:
        os.remove(tmp_path)


# ──────────────────────────────────────────
# メインループ
# ──────────────────────────────────────────

def main():
    start_time = datetime.now()  # 起動時刻を記録

    print("=" * 45)
    print("  人感センサー監視システム 起動")
    print(f"  Gmail監視: {GMAIL_ADDRESS}")
    print(f"  記録先:    {EXCEL_FILE}")
    print(f"  監視開始:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 45)
    print("Ctrl+C で終了\n")

    print("Gmailに接続しています...")
    mail = connect_gmail()

    last_record_time = 0
    last_uid  = ""
    last_date = ""

    while True:
        try:
            detected, last_uid, last_date = check_new_camera_mail(
                mail, last_uid, last_date, start_time
            )

            if detected:
                current_time = time.time()

                if (current_time - last_record_time) > COOLDOWN_SECONDS:
                    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    th   = get_temperature_humidity()
                    temp = th["temperature"]
                    hum  = th["humidity"]

                    write_to_excel([now, temp, hum])
                    print(f"✅ 人を検知しました！記録しました: {now}")

                    message = f"人を検知しました。現在の温度は{temp}度、湿度は{hum}パーセントです。"
                    send_line(message)
                    announce(message)

                    last_record_time = current_time
            else:
                print(f"[待機中] {datetime.now().strftime('%H:%M:%S')}")

        except imaplib.IMAP4.abort:
            print("  [Gmail] 接続が切れました。再接続しています...")
            try:
                mail = connect_gmail()
            except Exception as e:
                print(f"  [Gmail] 再接続失敗: {e}")

        except Exception as e:
            print(f"[エラー] {e}")

        time.sleep(2)


if __name__ == "__main__":
    main()
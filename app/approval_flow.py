import os
import sys
import time
import uuid
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.header import decode_header
import subprocess
import argparse
from typing import Optional, Tuple

# .env ファイルがある場合は自動読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# デフォルト設定
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_IMAP_SERVER = "imap.gmail.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_APPROVER = "makoto.insidesales@gmail.com"

def send_approval_request(
    task_name: str,
    task_id: str,
    approver: str,
    sender_email: str,
    sender_password: str,
    smtp_server: str,
    smtp_port: int
) -> bool:
    """
    承認依頼メールを送信します。
    """
    subject = f"[APPROVAL REQUIRED] Task: {task_name} (ID: {task_id})"
    body = f"""こんにちは、

以下のタスク実行の承認を求めています。

■ タスク名: {task_name}
■ タスクID: {task_id}
■ 実行対象コマンドの例: (指定された自動実行コマンド)

この処理を実行してよろしければ、本メールに返信し、本文の先頭に
「APPROVE」または「承認」と入力して送信してください。

却下する場合は「REJECT」または「却下」と入力してください。

※このメールは自動送信されています。タスクID: {task_id}
"""
    
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = approver

    try:
        print(f"[*] 承認依頼メールを送信中... 送信元: {sender_email} -> 宛先: {approver}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [approver], msg.as_string())
        server.quit()
        print("[+] 承認依頼メールの送信に成功しました。")
        return True
    except Exception as e:
        print(f"[-] メール送信エラー: {e}")
        return False

def check_for_approval(
    task_id: str,
    approver: str,
    sender_email: str,
    sender_password: str,
    imap_server: str,
    imap_port: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    IMAPサーバーをチェックし、該当するタスクIDに対する承認または却下の返信があるか確認します。
    返却値: (ステータス["APPROVE" | "REJECT" | None], 承認者のコメント)
    """
    try:
        # SSL接続
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(sender_email, sender_password)
        mail.select("inbox")

        # 承認者からの未読メール、または該当タスクIDを含むメールを検索
        # ここではタスクIDが件名や本文に含まれていることを基準にする
        search_criterion = f'TEXT "{task_id}"'
        status, messages = mail.search(None, search_criterion)
        
        if status != "OK":
            mail.logout()
            return None, None

        message_ids = messages[0].split()
        if not message_ids:
            mail.logout()
            return None, None

        # 最新のメッセージから順にチェック
        for msg_id in reversed(message_ids):
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            if res != "OK":
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    raw_email = response_part[1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # 送信元の確認
                    from_header = msg.get("From", "")
                    if approver not in from_header:
                        # 承認者以外からのメールは無視
                        continue
                    
                    # 本文の解析
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                except Exception:
                                    body = part.get_payload(decode=True).decode("iso-2022-jp", errors="ignore")
                                break
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        except Exception:
                            body = msg.get_payload(decode=True).decode("iso-2022-jp", errors="ignore")
                    
                    body_upper = body.upper().strip()
                    
                    # 承認・却下キーワードの確認
                    if "APPROVE" in body_upper or "承認" in body:
                        # 既読にしてから返す
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        mail.logout()
                        return "APPROVE", body.strip()
                    elif "REJECT" in body_upper or "却下" in body:
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        mail.logout()
                        return "REJECT", body.strip()

        mail.logout()
    except Exception as e:
        print(f"[-] メール受信確認エラー: {e}")
        
    return None, None

def run_command(command: str) -> bool:
    """
    承認されたコマンドを実行します。
    """
    print(f"[*] コマンドを実行します: {command}")
    try:
        # シェル経由でコマンドを実行し、出力をリアルタイム表示
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        rc = process.poll()
        if rc == 0:
            print("[+] コマンドの実行に成功しました。")
            return True
        else:
            print(f"[-] コマンドがエラー終了しました (Exit Code: {rc})")
            return False
    except Exception as e:
        print(f"[-] コマンド実行中に例外が発生しました: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="メール返信による承認制御フローを実行します。")
    parser.add_argument("--task", required=True, help="実行するタスク名")
    parser.add_argument("--command", required=True, help="承認後に実行するシェルコマンド")
    parser.add_argument("--approver", default=DEFAULT_APPROVER, help="承認者のメールアドレス")
    parser.add_argument("--interval", type=int, default=15, help="IMAPポーリングの間隔(秒)")
    parser.add_argument("--timeout", type=int, default=1800, help="承認待ちのタイムアウト時間(秒、デフォルト30分)")
    parser.add_argument("--simulate", action="store_true", help="メール送受信を行わず、コンソール上で承認シミュレーションを行います。")
    
    args = parser.parse_args()

    task_id = str(uuid.uuid4())[:8]
    print("==================================================")
    print(f"🛡️ Mail Approval Flow System Started (Task ID: {task_id})")
    print(f"■ タスク: {args.task}")
    print(f"■ コマンド: {args.command}")
    print(f"■ 承認者: {args.approver}")
    print("==================================================")

    if args.simulate:
        print("[*] シミュレーションモードで起動しました。")
        print(f"[MAIL SIMULATION] To: {args.approver} / Subject: [APPROVAL REQUIRED] Task: {args.task} (ID: {task_id})")
        print("コンソールで承認を入力してください。")
        user_choice = input("タスクを承認しますか？ (y/approve = 承認, n/reject = 却下): ").strip().lower()
        if user_choice in ["y", "yes", "approve", "承認"]:
            print("[+] 承認されました (シミュレーション)")
            run_command(args.command)
            sys.exit(0)
        else:
            print("[-] 却下されました (シミュレーション)")
            sys.exit(1)

    # 環境変数からSMTP/IMAP接続情報を取得
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", DEFAULT_SMTP_SERVER)
    try:
        smtp_port = int(os.getenv("SMTP_PORT", DEFAULT_SMTP_PORT))
    except ValueError:
        smtp_port = DEFAULT_SMTP_PORT
    imap_server = os.getenv("IMAP_SERVER", DEFAULT_IMAP_SERVER)
    try:
        imap_port = int(os.getenv("IMAP_PORT", DEFAULT_IMAP_PORT))
    except ValueError:
        imap_port = DEFAULT_IMAP_PORT

    if not sender_email or not sender_password:
        print("[-] エラー: 環境変数 SENDER_EMAIL または SENDER_PASSWORD が設定されていません。")
        print("    実際のメール送受信を行うには、.envファイルを作成するか、環境変数を設定してください。")
        print("    例: SENDER_EMAIL=your-bot@gmail.com, SENDER_PASSWORD=your-app-password")
        print("\n    提示: ローカルで動作検証を行う場合は --simulate オプションを使用できます。")
        sys.exit(1)

    # 1. 承認依頼メールを送信
    success = send_approval_request(
        task_name=args.task,
        task_id=task_id,
        approver=args.approver,
        sender_email=sender_email,
        sender_password=sender_password,
        smtp_server=smtp_server,
        smtp_port=smtp_port
    )
    
    if not success:
        print("[-] 承認依頼メールの送信に失敗したため、フローを終了します。")
        sys.exit(1)

    # 2. 承認待ちの監視ループ
    print(f"[*] 承認メールの受信をお待ちしています... ({args.interval}秒おきにチェック, タイムアウト: {args.timeout}秒)")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > args.timeout:
            print(f"[-] タイムアウトエラー: 制限時間内に承認が得られませんでした ({args.timeout}秒経過)。")
            sys.exit(1)
            
        status, comment = check_for_approval(
            task_id=task_id,
            approver=args.approver,
            sender_email=sender_email,
            sender_password=sender_password,
            imap_server=imap_server,
            imap_port=imap_port
        )
        
        if status == "APPROVE":
            print("\n[+] ==========================================")
            print(f"[+] 承認されました！")
            if comment:
                print(f"[+] 承認者コメント: {comment}")
            print("[+] ==========================================\n")
            run_command(args.command)
            break
        elif status == "REJECT":
            print("\n[-] ==========================================")
            print(f"[-] 却下されました。")
            if comment:
                print(f"[-] 却下理由: {comment}")
            print("[-] ==========================================\n")
            sys.exit(1)
            
        # 進行状況表示
        sys.stdout.write(f"\r[*] 待機中... 経過時間: {int(elapsed)}秒")
        sys.stdout.flush()
        time.sleep(args.interval)

if __name__ == "__main__":
    main()

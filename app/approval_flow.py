import os
import re
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
    # スクリプトの親の親ディレクトリ（プロジェクトルート）にある.envを明示的に指定
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass



# デフォルト設定
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_IMAP_SERVER = "imap.gmail.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_APPROVER = os.getenv("APPROVER_EMAIL", "makoto.insidesales@gmail.com")

def test_connection(
    sender_email: str,
    sender_password: str,
    smtp_server: str,
    smtp_port: int,
    imap_server: str,
    imap_port: int
) -> bool:
    """
    SMTPおよびIMAPのサーバーログイン接続テストを行います。
    """
    print("==================================================")
    print("📧 メールサーバー接続および認証テストを開始します...")
    print("==================================================")
    
    # 1. SMTPテスト
    smtp_success = False
    try:
        print(f"[*] SMTP接続テスト中: {smtp_server}:{smtp_port} ...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        if smtp_server not in ("127.0.0.1", "localhost"):
            try:
                server.starttls()
            except Exception as e:
                print(f"[*] STARTTLSがサポートされていないかスキップされました: {e}")
        print(f"[*] SMTPログイン中: {sender_email} ...")
        server.login(sender_email, sender_password)
        server.quit()
        print("[+] SMTP接続 & ログイン成功！")
        smtp_success = True
    except Exception as e:
        print(f"[-] SMTPテスト失敗: {e}")
        
    # 2. IMAPテスト
    imap_success = False
    try:
        print(f"[*] IMAP接続テスト中: {imap_server}:{imap_port} ...")
        if imap_server in ("127.0.0.1", "localhost"):
            mail = imaplib.IMAP4(imap_server, imap_port)
        else:
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        print(f"[*] IMAPログイン中: {sender_email} ...")
        mail.login(sender_email, sender_password)
        mail.logout()
        print("[+] IMAP接続 & ログイン成功！")
        imap_success = True
    except Exception as e:
        print(f"[-] IMAPテスト失敗: {e}")
        
    print("==================================================")
    if smtp_success and imap_success:
        print("[+] 接続テスト結果: すべて成功！メール承認フローを開始できます。")
        return True
    else:
        print("[-] 接続テスト結果: 一部またはすべてのテストが失敗しました。設定を確認してください。")
        return False

def send_approval_request(
    task_name: str,
    task_id: str,
    approver: str,
    sender_email: str,
    sender_password: str,
    smtp_server: str,
    smtp_port: int,
    details: str = "",
    command: str = ""
) -> bool:
    """
    承認依頼メールを送信します。
    """
    subject = f"[APPROVAL REQUIRED] Task: {task_name} (ID: {task_id})"
    
    details_section = ""
    if details:
        details_section = f"\n■ タスク詳細 / 実行計画:\n----------------------------------------\n{details}\n----------------------------------------\n"
        
    body = f"""こんにちは、

以下のタスク実行の承認を求めています。

■ タスク名: {task_name}
■ タスクID: {task_id}
■ 実行対象コマンド: {command if command else task_name}
{details_section}
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
        if smtp_server not in ("127.0.0.1", "localhost"):
            try:
                server.starttls()
            except Exception as e:
                print(f"[*] STARTTLSがサポートされていないかスキップされました: {e}")
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [approver], msg.as_string())
        server.quit()
        print("[+] 承認依頼メールの送信に成功しました。")
        return True
    except Exception as e:
        print(f"[-] メール送信エラー: {e}")
        return False

def extract_reply_content(body: str) -> str:
    """
    メール本文から返信部分（引用やヘッダーを除いた、送信者が直接入力したコンテンツ）を抽出します。
    """
    if not body:
        return ""
    lines = body.splitlines()
    reply_lines = []
    
    # 一般的な引用開始パターン
    quote_headers = [
        re.compile(r"^\s*on\s+.*wrote:\s*$", re.IGNORECASE),
        re.compile(r"^\s*-+\s*original\s+message\s*-+\s*$", re.IGNORECASE),
        re.compile(r"^\s*From:\s+.*", re.IGNORECASE),
        re.compile(r"^\s*Sent:\s+.*", re.IGNORECASE),
        re.compile(r"^\s*To:\s+.*", re.IGNORECASE),
        re.compile(r"^\s*Subject:\s+.*", re.IGNORECASE),
        re.compile(r"^\s*\d{4}[-/.]\d{2}[-/.]\d{2}\s+\d{2}:\d{2}.*:$")
    ]
    
    for line in lines:
        stripped = line.strip()
        # 引用行 (行頭が '>') の場合はそこで終了
        if stripped.startswith(">"):
            break
            
        # 引用ヘッダーにマッチした場合は、それ以降をカット
        is_header = False
        for pattern in quote_headers:
            if pattern.match(stripped):
                is_header = True
                break
        if is_header:
            break
            
        reply_lines.append(line)
        
    return "\n".join(reply_lines).strip()

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
        if imap_server in ("127.0.0.1", "localhost"):
            mail = imaplib.IMAP4(imap_server, imap_port)
        else:
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(sender_email, sender_password)
        mail.select("inbox")

        # 承認者からの返信を検知するため、件名(SUBJECT)にタスクIDが含まれるメールを優先的に検索
        # TEXT検索はインデックスの遅延が大きいため、SUBJECT検索を用いることで高速かつ確実に検知します
        search_criterion = f'SUBJECT "{task_id}"'
        status, messages = mail.search(None, search_criterion)
        
        # もしSUBJECT検索で見つからない場合は、フォールバックとしてTEXT全体検索も試みる
        if status != "OK" or not messages[0].split():
            search_criterion_fallback = f'TEXT "{task_id}"'
            status, messages = mail.search(None, search_criterion_fallback)
        
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
                                payload = part.get_payload(decode=True)
                                if payload:
                                    try:
                                        body = payload.decode("utf-8", errors="ignore")
                                    except Exception:
                                        body = payload.decode("iso-2022-jp", errors="ignore")
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            try:
                                body = payload.decode("utf-8", errors="ignore")
                            except Exception:
                                body = payload.decode("iso-2022-jp", errors="ignore")
                    
                    reply_text = extract_reply_content(body)
                    reply_upper = reply_text.upper()
                    
                    # 承認・却下キーワードの定義 (より柔軟な返信に対応)
                    # 英語キーワードは部分一致による誤判定（例: REVIEWING の "NG"）を防ぐため単語境界(\b)を使用
                    approve_en = ["APPROVE", "OK", "PROCEED"]
                    reject_en = ["REJECT", "NG", "CANCEL"]
                    
                    approve_ja = ["承認", "許可", "了解"]
                    reject_ja = ["却下", "不可"]
                    
                    is_approved = (
                        any(re.search(rf"\b{kw}\b", reply_upper) for kw in approve_en) or
                        any(kw in reply_text for kw in approve_ja)
                    )
                    is_rejected = (
                        any(re.search(rf"\b{kw}\b", reply_upper) for kw in reject_en) or
                        any(kw in reply_text for kw in reject_ja)
                    )
                    
                    # 承認・却下キーワードの確認
                    if is_approved:
                        # 既読にしてから返す
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        mail.logout()
                        return "APPROVE", reply_text
                    elif is_rejected:
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        mail.logout()
                        return "REJECT", reply_text

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
    parser.add_argument("--task", help="実行するタスク名")
    parser.add_argument("--command", help="承認後に実行するシェルコマンド")
    parser.add_argument("--approver", default=DEFAULT_APPROVER, help="承認者のメールアドレス")
    parser.add_argument("--interval", type=int, default=15, help="IMAPポーリングの間隔(秒)")
    parser.add_argument("--timeout", type=int, default=1800, help="承認待ちのタイムアウト時間(秒、デフォルト30分)")
    parser.add_argument("--simulate", action="store_true", help="メール送受信を行わず、コンソール上で承認シミュレーションを行います。")
    parser.add_argument("--details", default="", help="タスクの詳細情報や計画内容")
    parser.add_argument("--test-connection", action="store_true", help="SMTP/IMAPのログイン接続テストを行います（タスク実行は行いません）。")
    
    args = parser.parse_args()

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

    # 接続テスト機能が有効な場合
    if args.test_connection:
        if not sender_email or not sender_password:
            print("[-] エラー: 環境変数 SENDER_EMAIL または SENDER_PASSWORD が設定されていません。")
            print("    テスト接続を行うには、.envファイルを作成するか、環境変数を設定してください。")
            sys.exit(1)
        success = test_connection(
            sender_email=sender_email,
            sender_password=sender_password,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            imap_server=imap_server,
            imap_port=imap_port
        )
        sys.exit(0 if success else 1)

    # 通常のタスク実行時に必須となる引数のチェック
    if not args.task or not args.command:
        parser.error("通常の実行には --task と --command が必須です（--test-connection を除く）。")

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
        smtp_port=smtp_port,
        details=args.details,
        command=args.command
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

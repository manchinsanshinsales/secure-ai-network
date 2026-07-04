import socket
import threading
import re
import time
import email
from email.mime.text import MIMEText
import base64

# メモリ上のメールボックス
# 各エントリは辞書: {"id": int, "raw": bytes, "seen": bool, "subject": str, "body": str, "from": str, "to": str}
mailbox = []
mailbox_lock = threading.Lock()
mail_counter = 0

def add_mail_to_mailbox(raw_mail_bytes):
    global mail_counter
    with mailbox_lock:
        mail_counter += 1
        msg = email.message_from_bytes(raw_mail_bytes)
        
        # 本文の抽出
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
                
        mail_entry = {
            "id": mail_counter,
            "raw": raw_mail_bytes,
            "seen": False,
            "subject": msg.get("Subject", ""),
            "body": body,
            "from": msg.get("From", ""),
            "to": msg.get("To", "")
        }
        mailbox.append(mail_entry)
        print(f"[Mock Mail Server] Inboxに新着メールを受信! ID: {mail_entry['id']}, From: {mail_entry['from']}, Subject: {mail_entry['subject']}")
        return mail_entry

def auto_reply_task(task_id, task_name, sender_email, approver_email):
    # 2秒後に自動承認返信を差し込む
    time.sleep(2)
    print(f"[Mock Mail Server] {approver_email} としてタスク {task_id} の自動承認返信を生成中...")
    
    reply_subject = f"Re: [APPROVAL REQUIRED] Task: {task_name} (ID: {task_id})"
    reply_body = f"APPROVE. (Auto-Approved by Mock Mail Server)\n\nOriginal Task ID: {task_id}"
    
    msg = MIMEText(reply_body, "plain", "utf-8")
    msg["Subject"] = reply_subject
    msg["From"] = approver_email
    msg["To"] = sender_email
    
    add_mail_to_mailbox(msg.as_bytes())

# SMTP 接続ハンドラ
def handle_smtp_client(client_socket):
    try:
        client_socket.sendall(b"220 Mock SMTP Server Ready\r\n")
        mail_data = []
        in_data = False
        sender = ""
        recipients = []
        
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            
            lines = data.split(b"\r\n")
            for i, line in enumerate(lines):
                # 最後の要素が空の場合は無視（スプリットの都合上）
                if i == len(lines) - 1 and not line:
                    continue
                
                if in_data:
                    if line == b".":
                        in_data = False
                        raw_email = b"\r\n".join(mail_data)
                        mail_entry = add_mail_to_mailbox(raw_email)
                        client_socket.sendall(b"250 OK: Message accepted\r\n")
                        
                        # タスクIDとタスク名がメール本文または件名にあれば、自動承認を起動
                        subj = mail_entry["subject"]
                        # 件名フォーマット: [APPROVAL REQUIRED] Task: {task_name} (ID: {task_id})
                        match = re.search(r"Task:\s*(.*?)\s*\(ID:\s*([a-zA-Z0-9_-]+)\)", subj)
                        if match:
                            task_name = match.group(1)
                            task_id = match.group(2)
                            threading.Thread(
                                target=auto_reply_task,
                                args=(task_id, task_name, mail_entry["from"], mail_entry["to"]),
                                daemon=True
                            ).start()
                    else:
                        mail_data.append(line)
                else:
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    if not line_str:
                        continue
                    
                    parts = line_str.split()
                    cmd = parts[0].upper() if parts else ""
                    
                    if cmd in ("EHLO", "HELO"):
                        client_socket.sendall(b"250-Hello local.test\r\n250-AUTH LOGIN\r\n250 OK\r\n")
                    elif cmd == "AUTH":
                        client_socket.sendall(b"334 VXNlcm5hbWU6\r\n") # Username:
                    elif len(line_str) > 10 and cmd not in ("MAIL", "RCPT", "DATA", "QUIT") and not line_str.startswith("250"):
                        # AUTHログイン時のIDやPWのやり取り（簡易デコード・応答）
                        if "username" in line_str.lower() or not line_str.endswith("="):
                            client_socket.sendall(b"334 UGFzc3dvcmQ6\r\n") # Password:
                        else:
                            client_socket.sendall(b"235 Authentication successful\r\n")
                    elif cmd.startswith("MAIL"):
                        sender = line_str
                        client_socket.sendall(b"250 OK\r\n")
                    elif cmd.startswith("RCPT"):
                        recipients.append(line_str)
                        client_socket.sendall(b"250 OK\r\n")
                    elif cmd == "DATA":
                        in_data = True
                        mail_data = []
                        client_socket.sendall(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                    elif cmd == "QUIT":
                        client_socket.sendall(b"221 Bye\r\n")
                        return
                    else:
                        client_socket.sendall(b"250 OK\r\n")
    except Exception as e:
        print(f"[Mock SMTP Error] {e}")
    finally:
        client_socket.close()

# IMAP 接続ハンドラ
def handle_imap_client(client_socket):
    try:
        client_socket.sendall(b"* OK Mock IMAP Server Ready\r\n")
        
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            
            line = data.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) < 2:
                continue
                
            tag = parts[0]
            cmd = parts[1].upper()
            
            if cmd == "CAPABILITY":
                client_socket.sendall(f"* CAPABILITY IMAP4rev1\r\n{tag} OK CAPABILITY completed\r\n".encode())
            elif cmd == "LOGIN":
                client_socket.sendall(f"{tag} OK LOGIN completed\r\n".encode())
            elif cmd == "SELECT":
                with mailbox_lock:
                    cnt = len(mailbox)
                client_socket.sendall(f"* {cnt} EXISTS\r\n* 0 RECENT\r\n{tag} OK [READ-WRITE] SELECT completed\r\n".encode())
            elif cmd == "SEARCH":
                # 例: SEARCH SUBJECT "task1234"
                search_term = ""
                search_str = " ".join(parts[2:])
                search_str = search_str.replace('"', '')
                
                # キーワード抽出
                match = re.search(r'(?:SUBJECT|TEXT)\s+(\S+)', search_str, re.IGNORECASE)
                if match:
                    search_term = match.group(1).lower()
                else:
                    search_term = parts[-1].lower()
                
                matching_ids = []
                with mailbox_lock:
                    for mail_entry in mailbox:
                        if (search_term in mail_entry["subject"].lower() or 
                            search_term in mail_entry["body"].lower()):
                            matching_ids.append(str(mail_entry["id"]))
                
                ids_str = " ".join(matching_ids)
                client_socket.sendall(f"* SEARCH {ids_str}\r\n{tag} OK SEARCH completed\r\n".encode())
            elif cmd == "FETCH":
                msg_id_str = parts[2]
                try:
                    msg_id = int(msg_id_str)
                except ValueError:
                    msg_id = 1
                
                target_mail = None
                with mailbox_lock:
                    for mail_entry in mailbox:
                        if mail_entry["id"] == msg_id:
                            target_mail = mail_entry
                            break
                            
                if target_mail:
                    raw_len = len(target_mail["raw"])
                    client_socket.sendall(f"* {msg_id} FETCH (RFC822 {{{raw_len}}}\r\n".encode() + target_mail["raw"] + b"\r\n)\r\n" + f"{tag} OK FETCH completed\r\n".encode())
                else:
                    client_socket.sendall(f"{tag} NO No such message\r\n".encode())
            elif cmd == "STORE":
                msg_id_str = parts[2]
                try:
                    msg_id = int(msg_id_str)
                except ValueError:
                    msg_id = 1
                    
                with mailbox_lock:
                    for mail_entry in mailbox:
                        if mail_entry["id"] == msg_id:
                            mail_entry["seen"] = True
                            break
                client_socket.sendall(f"* {msg_id} FETCH (FLAGS (\\Seen))\r\n{tag} OK STORE completed\r\n".encode())
            elif cmd == "LOGOUT":
                client_socket.sendall(f"* BYE Mock IMAP Server logging out\r\n{tag} OK LOGOUT completed\r\n".encode())
                return
            else:
                client_socket.sendall(f"{tag} OK {cmd} completed\r\n".encode())
                
    except Exception as e:
        print(f"[Mock IMAP Error] {e}")
    finally:
        client_socket.close()

def start_smtp_server(port=1025):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(5)
    print(f"[Mock Mail Server] SMTP Server listening on 127.0.0.1:{port}...")
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_smtp_client, args=(client,), daemon=True).start()

def start_imap_server(port=1143):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(5)
    print(f"[Mock Mail Server] IMAP Server listening on 127.0.0.1:{port}...")
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_imap_client, args=(client,), daemon=True).start()

if __name__ == "__main__":
    print("==================================================")
    print("🛡️  Mock SMTP & IMAP Mail Server Starting...")
    print("   SMTP Port: 1025 (Local Dev)")
    print("   IMAP Port: 1143 (Local Dev)")
    print("   Auto-Approve Delay: 2 seconds")
    print("==================================================")
    
    smtp_thread = threading.Thread(target=start_smtp_server, args=(1025,), daemon=True)
    imap_thread = threading.Thread(target=start_imap_server, args=(1143,), daemon=True)
    
    smtp_thread.start()
    imap_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Mock Mail Server] Stopping...")

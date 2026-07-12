import os
import json
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 設定情報の読み込み（ローカル環境変数またはデフォルト値）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "MOCK_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "MOCK_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini API の設定
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("[WARNING] GEMINI_API_KEY が設定されていません。AI応答はモックテキストを返します。")

# データファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAFE_INFO_PATH = os.path.join(BASE_DIR, "docs", "cafe_info.md")
TEST_QUESTIONS_PATH = os.path.join(BASE_DIR, "docs", "skills_test.json")
TEST_RESULTS_PATH = os.path.join(BASE_DIR, "records", "test_results.json")

# データの読み込み
def load_cafe_info():
    try:
        with open(CAFE_INFO_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"店舗情報の読み込みエラー: {e}")
        return "店舗情報は現在準備中です。"

def load_questions():
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"テスト問題の読み込みエラー: {e}")
        return []

CAFE_INFO = load_cafe_info()
QUESTIONS = load_questions()

# ユーザーのステート管理（インメモリ）
# 構造: { user_id: { "state": "normal" | "testing", "current_q": 0, "answers": [], "name": "" } }
user_states = {}

# テスト結果の保存
def save_test_result(user_id, name, score, passed):
    os.makedirs(os.path.dirname(TEST_RESULTS_PATH), exist_ok=True)
    results = []
    if os.path.exists(TEST_RESULTS_PATH):
        try:
            with open(TEST_RESULTS_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            results = []
    
    new_result = {
        "user_id": user_id,
        "name": name,
        "score": score,
        "passed": passed,
        "date": "2026-07-12T11:00:00" # 簡易的日付（実際はdatetime）
    }
    results.append(new_result)
    
    with open(TEST_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # マネージャー（管理者）への通知模擬
    notify_manager(new_result)

def notify_manager(result):
    status_str = "合格（時給アップ対象！）" if result["passed"] else "不合格"
    notification_msg = (
        f"【テスト結果報告】\n"
        f"アルバイトの {result['name']} さんがスキルテストを受験しました。\n"
        f"得点: {result['score']}点 / 30点 (3問中)\n"
        f"判定: {status_str}\n"
        f"日付: {result['date']}"
    )
    print("\n" + "="*40)
    print("🔔 マネージャーへの通知 (模擬)")
    print(notification_msg)
    print("="*40 + "\n")
    
    # 実運用では、ここで管理者のLINEユーザーID宛にプッシュメッセージを送信するなどのロジックが入る

# GeminiによるAI応答生成
def generate_ai_response(user_message):
    if not GEMINI_API_KEY:
        return "（モック応答）お問い合わせありがとうございます。店舗情報に基づいてAIが回答する仕組みです。"
    
    prompt = f"""
あなたはカフェ「Cafe Antigravity」の親切なAI店員です。
以下の店舗情報に基づいて、お客様からの質問に日本語で親切かつ簡潔に答えてください。
店舗情報に記載されていない内容については、適当に嘘をつかず「申し訳ありませんが、分かりかねます」と答えてください。

【店舗情報】
{CAFE_INFO}

【お客様からのメッセージ】
{user_message}
"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API エラー: {e}")
        return "申し訳ありません。システムエラーによりAI応答を生成できませんでした。"

# LINEへの返信送信
def reply_to_line(reply_token, text):
    if reply_token == "MOCK_TOKEN":
        print(f"[MOCK LINE REPLY] Token: {reply_token}, Message: {text}")
        return
    
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code != 200:
            print(f"LINE API 返信エラー: {res.text}")
    except Exception as e:
        print(f"LINE API 送信エラー: {e}")

# ボットの対話ロジック処理
def handle_bot_logic(user_id, reply_token, user_message):
    state_info = user_states.get(user_id, {"state": "normal"})
    
    # 1. テスト中ではない場合
    if state_info["state"] == "normal":
        if user_message == "テスト開始":
            user_states[user_id] = {
                "state": "get_name",
                "current_q": 0,
                "answers": [],
                "name": ""
            }
            reply_to_line(reply_token, "アルバイト向けスキルテストを開始します。まず、お名前（フルネーム）を送信してください。")
            return
        
        # 通常の店舗問い合わせ応答（Gemini API）
        response_text = generate_ai_response(user_message)
        reply_to_line(reply_token, response_text)
    
    # 2. 名前を入力してもらうフェーズ
    elif state_info["state"] == "get_name":
        name = user_message.strip()
        state_info["name"] = name
        state_info["state"] = "testing"
        
        # 最初の問題を送信
        q = QUESTIONS[0]
        question_text = (
            f"第1問:\n{q['question']}\n\n" + "\n".join(q['options']) + 
            "\n\n※回答は A, B, C, D のいずれかのアルファベットで送信してください。"
        )
        reply_to_line(reply_token, f"{name} さんですね。それではテストを開始します。\n\n{question_text}")
    
    # 3. テスト実施中のフェーズ
    elif state_info["state"] == "testing":
        current_q_idx = state_info["current_q"]
        q = QUESTIONS[current_q_idx]
        
        # 回答の検証（簡易的）
        ans = user_message.strip().upper()
        if ans not in ["A", "B", "C", "D"]:
            reply_to_line(reply_token, "A, B, C, D のいずれかで回答してください。")
            return
        
        # 正誤判定
        # 選択肢のインデックス（0: A, 1: B, 2: C, 3: D）
        ans_idx = ["A", "B", "C", "D"].index(ans)
        is_correct = (ans_idx == q["answer"])
        state_info["answers"].append({
            "question_id": q["id"],
            "user_answer": ans,
            "correct": is_correct
        })
        
        next_q_idx = current_q_idx + 1
        if next_q_idx < len(QUESTIONS):
            # 次の問題に進む
            state_info["current_q"] = next_q_idx
            next_q = QUESTIONS[next_q_idx]
            question_text = (
                f"第{next_q_idx + 1}問:\n{next_q['question']}\n\n" + "\n".join(next_q['options']) + 
                "\n\n※回答は A, B, C, D のいずれかのアルファベットで送信してください。"
            )
            reply_to_line(reply_token, question_text)
        else:
            # テスト完了、結果集計
            correct_count = sum(1 for a in state_info["answers"] if a["correct"])
            total_score = correct_count * 10  # 1問10点
            passed = (total_score >= 20)  # 2問以上正解（20点以上）で合格
            
            result_msg = (
                f"【テスト終了】\nお疲れ様でした、{state_info['name']} さん。\n\n"
                f"結果: {total_score}点 / 30点\n"
                f"判定: {'合格🎉（時給アップ！）' if passed else '不合格😢（時給は上がりません。マニュアルを読み直してください。）'}\n\n"
                f"結果はマネージャーへ報告されました。"
            )
            reply_to_line(reply_token, result_msg)
            
            # 結果を保存＆通知
            save_test_result(user_id, state_info["name"], total_score, passed)
            
            # ステートを通常に戻す
            user_states[user_id] = {"state": "normal"}

# LINE Webhookのエンドポイント
@app.route("/webhook", methods=["POST"])
def webhook():
    # 本番環境ではここで署名検証（LINE_CHANNEL_SECRETを使用）を行うのが望ましい
    body = request.get_data(as_text=True)
    try:
        data = request.get_json()
    except Exception:
        return "Invalid JSON", 400
        
    if not data or "events" not in data:
        return "OK", 200
        
    for event in data["events"]:
        if event.get("type") == "message" and event["message"].get("type") == "text":
            user_id = event["source"]["userId"]
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]
            
            handle_bot_logic(user_id, reply_token, user_message)
            
    return "OK", 200

# ローカルデバッグ用の対話API
@app.route("/debug/chat", methods=["POST"])
def debug_chat():
    data = request.get_json()
    user_id = data.get("userId", "debug-user-1")
    message = data.get("message", "")
    
    # 応答ログをモック
    print(f"\n[USER INPUT] {user_id}: {message}")
    
    # 応答をキャプチャするために一時的に LINE 送信をモックフック
    responses = []
    def mock_reply(token, text):
        responses.append(text)
    
    global reply_to_line
    original_reply = reply_to_line
    reply_to_line = mock_reply
    
    try:
        handle_bot_logic(user_id, "MOCK_TOKEN", message)
    finally:
        reply_to_line = original_reply
        
    return jsonify({
        "status": "success",
        "responses": responses,
        "user_state": user_states.get(user_id, {"state": "normal"})
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

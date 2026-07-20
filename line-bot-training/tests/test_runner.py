import json
import requests
import time
import subprocess
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Flaskアプリをサブプロセスで起動
print("Starting Flask app...")
# 環境変数をクリアにする（Gemini API Keyを設定しない場合はモック応答になる）
env = os.environ.copy()
env["GEMINI_API_KEY"] = "" # 今回はローカル疎通のためモック応答で検証

server_process = subprocess.Popen(
    [os.path.join(BASE_DIR, ".venv", "bin", "python"), os.path.join(BASE_DIR, "app", "app.py")],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)
time.sleep(3) # 起動を待つ

CHAT_URL = "http://localhost:5001/debug/chat"

def send_message(user_id, msg):
    payload = {"userId": user_id, "message": msg}
    res = requests.post(CHAT_URL, json=payload)
    return res.json()

try:
    user_id = "test-alba-01"
    
    # シナリオ1: 通常問い合わせ
    print("\n--- Test 1: Normal FAQ ---")
    res = send_message(user_id, "営業時間について教えて")
    print(f"Reply: {res['responses']}")
    assert len(res['responses']) > 0
    assert "モック" in res['responses'][0]
    
    # シナリオ2: テスト開始
    print("\n--- Test 2: Start Skill Test ---")
    res = send_message(user_id, "テスト開始")
    print(f"Reply: {res['responses']}")
    assert "お名前" in res['responses'][0]
    
    # シナリオ3: 名前入力
    print("\n--- Test 3: Input Name ---")
    res = send_message(user_id, "山田太郎")
    print(f"Reply: {res['responses']}")
    assert "第1問" in res['responses'][0]
    
    # シナリオ4: Q1回答 (正解: B)
    print("\n--- Test 4: Answer Q1 ---")
    res = send_message(user_id, "B")
    print(f"Reply: {res['responses']}")
    assert "第2問" in res['responses'][0]
    
    # シナリオ5: Q2回答 (正解: B)
    print("\n--- Test 5: Answer Q2 ---")
    res = send_message(user_id, "B")
    print(f"Reply: {res['responses']}")
    assert "第3問" in res['responses'][0]
    
    # シナリオ6: Q3回答 (正解: C。3問中3問正解なので、30点で合格になる)
    print("\n--- Test 6: Answer Q3 (Correct) ---")
    res = send_message(user_id, "C")
    print(f"Reply: {res['responses']}")
    assert "テスト終了" in res['responses'][0]
    assert "合格" in res['responses'][0]
    
    # テスト結果が記録ファイルに保存されたか確認
    print("\n--- Test 7: Verify saved results ---")
    results_file = os.path.join(BASE_DIR, "app", "records", "test_results.json")
    assert os.path.exists(results_file)
    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)
        last_result = results[-1]
        print(f"Saved Result: {last_result}")
        assert last_result["name"] == "山田太郎"
        assert last_result["score"] == 30
        assert last_result["passed"] is True
        
    # シナリオ8: Dialogflow CX Webhookのテスト
    print("\n--- Test 8: Dialogflow CX Webhook ---")
    df_payload = {
        "sessionInfo": {
            "session": "projects/my-project/agent/sessions/test-alba-dialogflow-01",
            "parameters": {
                "alba_name": "鈴木花子",
                "q1_answer": "B",
                "q2_answer": "B",
                "q3_answer": "A"
            }
        }
    }
    df_res = requests.post("http://localhost:5001/dialogflow/webhook", json=df_payload).json()
    reply_text = df_res["fulfillmentResponse"]["messages"][0]["text"]["text"][0]
    print(f"Dialogflow Reply: {reply_text}")
    assert "鈴木花子" in reply_text
    assert "20点" in reply_text
    assert "合格" in reply_text
    
    # 記録の検証
    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)
        last_result = results[-1]
        print(f"Saved Dialogflow Result: {last_result}")
        assert last_result["name"] == "鈴木花子"
        assert last_result["score"] == 20
        assert last_result["passed"] is True
        
    print("\n🎉 All tests passed successfully!")
    
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    # プロセスの出力をデバッグ表示
    try:
        stdout, stderr = server_process.communicate(timeout=2)
        print("Server Stdout:", stdout)
        print("Server Stderr:", stderr)
    except Exception:
        pass
finally:
    # サーバーを確実に終了
    server_process.terminate()
    server_process.wait()

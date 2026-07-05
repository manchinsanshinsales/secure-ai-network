import os
import sys
import json
import time
import requests

def load_file(filepath):
    if not os.path.exists(filepath):
        print(f"エラー: ファイルが見つかりません - {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def run_gemini(prompt, contract_content, api_key):
    print("Gemini API (gemini-2.5-flash) を呼び出し中...")
    
    # プロンプトの結合
    full_prompt = f"{prompt}\n\n【対象の契約書】\n{contract_content}"
    
    start_time = time.time()
    try:
        # 新しい google-genai SDK の使用を試みる
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            response_text = response.text
        except ImportError:
            # 古い google-generativeai SDK のフォールバック
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            response_text = response.text
            
        elapsed_time = time.time() - start_time
        return {
            "success": True,
            "response": response_text,
            "elapsed_time_sec": elapsed_time,
            "error": None
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Gemini API 呼び出し中にエラーが発生しました: {e}")
        return {
            "success": False,
            "response": None,
            "elapsed_time_sec": elapsed_time,
            "error": str(e)
        }

def run_ollama(prompt, contract_content, model_name):
    print(f"Ollama API を呼び出し中 (モデル: {model_name})...")
    
    full_prompt = f"{prompt}\n\n【対象の契約書】\n{contract_content}"
    
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result_data = response.json()
            response_text = result_data.get("response", "")
            return {
                "success": True,
                "response": response_text,
                "elapsed_time_sec": elapsed_time,
                "error": None
            }
        else:
            return {
                "success": False,
                "response": None,
                "elapsed_time_sec": elapsed_time,
                "error": f"HTTP Status {response.status_code}: {response.text}"
            }
    except requests.exceptions.ConnectionError:
        elapsed_time = time.time() - start_time
        print("接続エラー: Ollamaが起動していないか、オフラインです。")
        return {
            "success": False,
            "response": None,
            "elapsed_time_sec": elapsed_time,
            "error": "Ollama connection refused (is it running?)"
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Ollama API 呼び出し中にエラーが発生しました: {e}")
        return {
            "success": False,
            "response": None,
            "elapsed_time_sec": elapsed_time,
            "error": str(e)
        }

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contract_path = os.path.join(base_dir, "records", "dummy_contract.md")
    prompt_path = os.path.join(base_dir, "records", "evaluation_prompt.md")
    results_json_path = os.path.join(base_dir, "records", "benchmark_results.json")
    
    print("=== クラウド(Gemini) vs オンプレ(Ollama) 比較ベンチマーク ===")
    contract_content = load_file(contract_path)
    prompt_content = load_file(prompt_path)
    
    # APIキーの取得
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("警告: 環境変数 GEMINI_API_KEY が設定されていません。Gemini の測定はスキップされます。")
        
    # Ollama モデル名の取得
    ollama_model = os.environ.get("OLLAMA_MODEL", "gemma2:9b")
    
    results = {}
    
    # 1. Gemini の実行
    if api_key:
        gemini_res = run_gemini(prompt_content, contract_content, api_key)
        results["gemini"] = gemini_res
        if gemini_res["success"]:
            print(f"➔ Gemini 実行成功 (処理時間: {gemini_res['elapsed_time_sec']:.2f} 秒)")
    else:
        results["gemini"] = {"success": False, "error": "API Key missing"}
        
    # 2. Ollama の実行
    ollama_res = run_ollama(prompt_content, contract_content, ollama_model)
    results["ollama"] = ollama_res
    if ollama_res["success"]:
        print(f"➔ Ollama ({ollama_model}) 実行成功 (処理時間: {ollama_res['elapsed_time_sec']:.2f} 秒)")
        
    # 結果の保存
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nベンチマーク結果を保存しました: {results_json_path}")
    
    # 結果の簡易表示
    print("\n=== 簡易比較結果 ===")
    print(f"{'モデル':<25} | {'ステータス':<10} | {'処理時間 (秒)':<15}")
    print("-" * 60)
    
    for name, res in [("Gemini 2.5 Flash", results.get("gemini")), (f"Ollama ({ollama_model})", results.get("ollama"))]:
        status = "成功" if res and res["success"] else "失敗/スキップ"
        elapsed = f"{res['elapsed_time_sec']:.2f}" if res and res["success"] else "N/A"
        print(f"{name:<25} | {status:<10} | {elapsed:<15}")

if __name__ == "__main__":
    main()

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

# 簡易DLPゲートウェイ (マスキングプロセッサ)
def dlp_mask(text):
    mask_map = {
        "開示株式会社": "[COMPANY_A]",
        "受領テクノロジー株式会社": "[COMPANY_B]",
        "開示 太郎": "[PERSON_A]",
        "受領 次郎": "[PERSON_B]",
    }
    masked_text = text
    for original, masked in mask_map.items():
        masked_text = masked_text.replace(original, masked)
    return masked_text, mask_map

def dlp_unmask(masked_text, mask_map):
    unmasked_text = masked_text
    for original, masked in mask_map.items():
        unmasked_text = unmasked_text.replace(masked, original)
    return unmasked_text

def run_gemini(prompt, contract_content, api_key, model_name="gemini-3.5-flash"):
    print(f"セキュアAIゲートウェイ経由で {model_name} を呼び出し中 (DLPマスキング適用)...")
    
    # 1. DLPゲートウェイでの個人情報/企業名のマスキング実行
    masked_contract, mask_map = dlp_mask(contract_content)
    masked_prompt, _ = dlp_mask(prompt)
    
    # マスキングされたプロンプトの結合
    full_prompt = f"{masked_prompt}\n\n【対象の契約書 (DLPマスク済)】\n{masked_contract}"
    
    start_time = time.time()
    try:
        # 新しい google-genai SDK の使用を試みる
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt
            )
            response_text = response.text
        except ImportError:
            # 古い google-generativeai SDK のフォールバック
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            # マッピングモデル名
            legacy_model = "gemini-1.5-flash" if "lite" in model_name else "gemini-1.5-flash"
            model = genai.GenerativeModel(legacy_model)
            response = model.generate_content(full_prompt)
            response_text = response.text
            
        elapsed_time = time.time() - start_time
        
        # 2. DLPゲートウェイでのアンマスキング (データの復元)
        unmasked_response = dlp_unmask(response_text, mask_map)
        
        return {
            "success": True,
            "masked_prompt_preview": full_prompt[:200] + "...",
            "response": unmasked_response,
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
    print(f"完全閉鎖ローカル環境で Ollama を呼び出し中 (生データ処理, モデル: {model_name})...")
    
    # ローカル環境は機密が保持されるため、マスキングなしで生データを送信
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
    
    print("=== クラウド(DLPゲートウェイ + Gemini) vs オンプレ(Ollama/Gemma) ===")
    contract_content = load_file(contract_path)
    prompt_content = load_file(prompt_path)
    
    # APIキーの取得
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("警告: 環境変数 GEMINI_API_KEY が設定されていません。Gemini の測定はスキップされます。")
        
    # 各種環境変数
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    ollama_model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    
    results = {}
    
    # 1. Gemini の実行 (DLPゲートウェイシミュレーション含む)
    if api_key:
        gemini_res = run_gemini(prompt_content, contract_content, api_key, gemini_model)
        results["gemini"] = gemini_res
        if gemini_res["success"]:
            print(f"➔ Gemini ({gemini_model}) 実行成功 (処理時間: {gemini_res['elapsed_time_sec']:.2f} 秒)")
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
    print(f"{'モデル / 構成':<30} | {'ステータス':<10} | {'処理時間 (秒)':<15}")
    print("-" * 65)
    
    gemini_display = f"Gemini ({gemini_model})"
    status_gemini = "成功(DLP適用)" if results.get("gemini") and results["gemini"]["success"] else "失敗/スキップ"
    elapsed_gemini = f"{results['gemini']['elapsed_time_sec']:.2f}" if results.get("gemini") and results["gemini"]["success"] else "N/A"
    
    ollama_display = f"Ollama ({ollama_model})"
    status_ollama = "成功(完全閉域)" if results.get("ollama") and results["ollama"]["success"] else "失敗/スキップ"
    elapsed_ollama = f"{results['ollama']['elapsed_time_sec']:.2f}" if results.get("ollama") and results["ollama"]["success"] else "N/A"
    
    print(f"{gemini_display:<30} | {status_gemini:<10} | {elapsed_gemini:<15}")
    print(f"{ollama_display:<30} | {status_ollama:<10} | {elapsed_ollama:<15}")

if __name__ == "__main__":
    main()

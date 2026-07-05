import streamlit as st
from masking import mask_text, unmask_text
from llm_client import MockLLMClient, GeminiClient

# サンプル契約書の定義
SAMPLE_CONTRACT = """業務委託契約書

委託者である株式会社マコト商事（以下「甲」という）と、受託者である山田 太郎（以下「乙」という）は、業務委託に関して以下の通り契約を締結する。

第1条（業務内容）
甲は乙に対し、ウェブアプリケーションの開発業務（以下「本業務」という）を委託し、乙はこれを受託する。

第2条（委託料および支払方法）
甲は乙に対し、本業務の対価として金 1,000,000円（消費税別）を支払う。
支払期日は、本業務完了後の最初の月末（2026年8月31日）とする。

第3条（秘密保持）
乙は、本業務に関連して甲から開示された一切の機密情報を、甲の書面による事前の承諾なく第三者に開示または漏洩してはならない。

第4条（契約締結）
本契約の成立を証するため、本書２通を作成し、甲乙記名押印のうえ、各１通を保有する。

2026年7月3日
甲：東京都渋谷区渋谷1-1-1
    株式会社マコト商事
    代表取締役　戸塚 誠
乙：東京都新宿区新宿2-2-2
    山田 太郎
"""

def main():
    # ページ設定
    st.set_page_config(
        page_title="セキュア契約書リーガルチェック PoC",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # スタイルの調整 (見た目の改善)
    st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1E3A8A;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #3B82F6;
        padding-left: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # タイトル表示
    st.markdown('<div class="main-title">📄 セキュア契約書リーガルチェック PoC</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">外部APIに機密情報を送信せず、手元のローカル処理で安全にリーガルチェックを行うデモアプリケーション</div>', unsafe_allow_html=True)

    # サイドバーの構築
    st.sidebar.header("⚙️ 設定・コントロール")
    
    # 動作モードの選択
    mode = st.sidebar.radio(
        "動作モード",
        ["デモモード (API不要・モック応答)", "本番モード (Gemini API使用)"]
    )
    
    # APIキー入力（本番モード時のみ）
    api_key = ""
    if mode == "本番モード (Gemini API使用)":
        api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Google AI Studio から取得したAPIキーを入力してください。")
        if not api_key:
            st.sidebar.warning("⚠️ APIキーを入力してください。")
            
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 マスキング項目設定")
    mask_org = st.sidebar.checkbox("組織・会社名", value=True, help="株式会社〇〇などの組織名をダミー化します。")
    mask_per = st.sidebar.checkbox("個人名 (代表者・当事者)", value=True, help="代表取締役〇〇や、契約当事者名をダミー化します。")
    mask_money = st.sidebar.checkbox("金額・通貨", value=True, help="契約金額や単価をダミー化します。")
    mask_date = st.sidebar.checkbox("日付", value=True, help="契約日や支払期限をダミー化します。")
    
    # マスキングオプションの辞書作成
    mask_options = {
        "ORG": mask_org,
        "PER": mask_per,
        "MONEY": mask_money,
        "DATE": mask_date
    }

    # メイン入力エリア
    st.markdown('<div class="section-header">【ステップ 1】契約書テキストの入力</div>', unsafe_allow_html=True)
    
    # サンプル読み込みボタン
    if st.button("サンプル契約書を読み込む"):
        st.session_state.contract_text = SAMPLE_CONTRACT
        
    # テキスト入力エリア
    contract_text = st.text_area(
        "契約書テキスト（または以下のテキストエリアに直接入力してください）",
        value=st.session_state.get("contract_text", ""),
        height=300,
        placeholder="契約書のテキストをここに貼り付けるか、上のボタンでサンプルを読み込んでください..."
    )
    
    # テキストが更新されたらセッションを更新
    st.session_state.contract_text = contract_text

    # 実行ボタン
    execute_button = st.button("安全にリーガルチェックを実行", type="primary")

    if execute_button:
        if not contract_text.strip():
            st.error("契約書テキストが入力されていません。")
            return
            
        if mode == "本番モード (Gemini API使用)" and not api_key:
            st.error("本番モードの実行にはGemini APIキーが必要です。サイドバーから入力してください。")
            return

        with st.spinner("安全なマスキング処理とリーガルチェックを実行中..."):
            # 1. ローカルでマスキング（機密情報のダミー化）
            masked_text, mapping_dict = mask_text(contract_text, mask_options)
            
            # 2. プロンプトの構築
            prompt = f"""あなたは優秀な弁護士、および法務のスペシャリストです。
以下の契約書テキストについて、リーガルチェックを行い、レビューレポートを作成してください。

【レビューの指示項目】
1. 甲および乙にとって不利な条件や、一般的な契約と比べて不自然な条項がないか。
2. 欠落している重要な条項（例：遅延損害金、反社会的勢力排除、管轄裁判所など）がないか。
3. 修正すべき具体的な文言とその法的・実務的理由。

【重要なセキュリティルール】
- 安全対策のため、契約書内の特定の固有名詞や金額などは、[ORGANIZATION_1] や [MONEY_1] のように匿名化されています。
- レビュー結果を記述する際も、この匿名化された表現（[ORGANIZATION_1] や [MONEY_1] など）のまま回答してください。元の社名や金額を勝手に推測して回答に含めてはいけません。

【契約書テキスト】
{masked_text}
"""
            
            # 3. LLMクライアントの選択と実行
            if mode == "デモモード (API不要・モック応答)":
                client = MockLLMClient()
            else:
                client = GeminiClient(api_key=api_key)
                
            # LLMへリクエスト送信 (匿名データのみ)
            raw_response = client.generate_response(prompt)
            
            # 4. 返答テキストのアンマスキング（復元）
            final_response = unmask_text(raw_response, mapping_dict)
            
            # 結果表示エリアの作成
            st.markdown('<div class="section-header">【ステップ 2】解析結果</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🛡️ 外部APIに送信された安全なテキスト（マスキング済）")
                st.info("※ このように個人名や会社名、金額などのプライベートなデータはプレースホルダーに置換されて送信されます。")
                st.code(masked_text, language="markdown")
                
            with col2:
                st.subheader("💡 復元されたレビュー結果")
                st.success("※ LLMから返ってきた匿名の指摘を、手元の対応表で元の名前や金額に安全に復元しました。")
                st.markdown(final_response)
                
            # デバッグ用対応表の表示
            st.markdown("---")
            with st.expander("🔍 ローカルで一時保持されているデータ対応表（マッピングテーブル）を確認"):
                st.write("※ このデータは外部APIには送信されず、ユーザーの端末（ブラウザセッション）内のみで保持されています。")
                if mapping_dict:
                    st.json(mapping_dict)
                else:
                    st.write("マスキングされたデータはありませんでした。")

if __name__ == "__main__":
    main()

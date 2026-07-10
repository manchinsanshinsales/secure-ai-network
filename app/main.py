import sys
import os

# オフライン（エアギャップ）環境でWebビューが正常にロードされるよう、CDNからのアセット取得をオフにしローカルアセットを強制する
os.environ["FLET_WEB_NO_CDN"] = "true"

# Add workspace root to search path to allow resolving 'app.*'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft
import threading
import app.database as db
import app.rag as rag

# Ensure database is initialized on startup
db.initialize_db()

def parse_thinking_and_answer(raw_text):
    """Parses raw streamed LLM text to separate <thinking> block from the final answer."""
    if "<thinking>" in raw_text:
        parts = raw_text.split("<thinking>", 1)
        before_thinking = parts[0]
        rest = parts[1]
        if "</thinking>" in rest:
            sub_parts = rest.split("</thinking>", 1)
            thinking = sub_parts[0]
            after_thinking = sub_parts[1]
            return thinking.strip(), (before_thinking + after_thinking).strip()
        else:
            return rest.strip(), before_thinking.strip()
    return "", raw_text.strip()

def main(page: ft.Page):
    page.title = "On-Premise RAG Studio"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#13151A"  # Deep slate background
    page.padding = 0
    
    # オフライン環境用の日本語フォント。
    # Webモードではブラウザがフォントを取得するため、OSの絶対パスは使えず
    # assets_dir 配下のファイルをURLパスで参照する必要がある（.ttcではなく単一.ttfを使う）
    page.fonts = {
        "Noto Sans JP": "/fonts/NotoSansJP-VF.ttf"
    }

    # Custom fonts configuration
    page.theme = ft.Theme(
        color_scheme_seed="indigo",
        font_family="Noto Sans JP",
        visual_density=ft.VisualDensity.COMFORTABLE
    )

    # State variables
    top_k_ref = 3
    system_prompt_ref = ""
    llm_model_ref = "gemma4:12b"
    
    # UI Controls
    chat_list = ft.ListView(
        expand=True,
        spacing=15,
        padding=20,
        auto_scroll=True
    )
    
    query_input = ft.TextField(
        hint_text="ローカルドキュメントについて質問する...",
        expand=True,
        border_radius=12,
        border_color="#3A3F50",
        bgcolor="#1E222B",
        content_padding=15,
        on_submit=lambda e: send_message(e)
    )
    
    send_btn = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color="indigo300",
        on_click=lambda e: send_message(e),
        tooltip="送信"
    )
    
    doc_list_column = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )
    
    # Loading indicators
    indexing_progress = ft.ProgressBar(visible=False, color="emerald400")
    
    # Toast notification helper
    def show_toast(message, is_error=False):
        page.open(ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor="red800" if is_error else "green800"
        ))

    # Load and render indexed documents
    def refresh_document_list():
        doc_list_column.controls.clear()
        docs = db.get_all_documents()
        if not docs:
            doc_list_column.controls.append(
                ft.Text("登録されたドキュメントはありません", color="#5C6479", size=13, italic=True)
            )
        for doc_id, filename, filepath, size, added_at in docs:
            # Format file size
            size_kb = size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{(size_kb/1024):.1f} MB"
            
            def make_delete_handler(d_id=doc_id, name=filename):
                return lambda e: delete_document(d_id, name)
                
            doc_list_column.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ARTICLE, color="indigo300", size=20),
                        ft.Column([
                            ft.Text(filename, size=13, weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS, width=150, color="#E2E8F0"),
                            ft.Text(size_str, size=11, color="#6B7280")
                        ], spacing=2, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color="red400",
                            icon_size=18,
                            tooltip="削除",
                            on_click=make_delete_handler()
                        )
                    ]),
                    bgcolor="#1E222B",
                    padding=10,
                    border_radius=8,
                    border=ft.Border(
                        ft.BorderSide(1, "#2D313E"),
                        ft.BorderSide(1, "#2D313E"),
                        ft.BorderSide(1, "#2D313E"),
                        ft.BorderSide(1, "#2D313E")
                    )
                )
            )
        page.update()

    def delete_document(doc_id, name):
        try:
            db.delete_document(doc_id)
            show_toast(f"「{name}」を削除しました")
            refresh_document_list()
        except Exception as ex:
            show_toast(f"削除エラー: {str(ex)}", is_error=True)

    # Document Picker logic
    def ingest_files(picked_files):
        """picked_files: list of (display_name, local_path) tuples."""
        indexing_progress.visible = True
        page.update()

        # Ingest files in background to keep UI responsive
        def ingest():
            success_count = 0
            for name, path in picked_files:
                try:
                    rag.register_document_to_rag(path)
                    success_count += 1
                except Exception as ex:
                    show_toast(f"「{name}」の読み込みに失敗: {str(ex)}", is_error=True)

            indexing_progress.visible = False
            if success_count > 0:
                show_toast(f"{success_count}個のファイルを登録・インデックス化しました")
            refresh_document_list()

        threading.Thread(target=ingest, daemon=True).start()

    async def pick_and_register(e):
        files = await file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf", "txt", "md"],
            with_data=True  # Webモードではpathが取れないため中身を受け取る
        )
        if not files:
            return

        resolved = []
        for f in files:
            if f.path:
                # デスクトップモード: ローカルパスをそのまま使用
                resolved.append((f.name, f.path))
            elif f.bytes is not None:
                # Webモード: 受信したバイト列をuploadsフォルダに保存して登録
                uploads_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "uploads"
                )
                os.makedirs(uploads_dir, exist_ok=True)
                dest = os.path.join(uploads_dir, f.name)
                with open(dest, "wb") as out:
                    out.write(f.bytes)
                resolved.append((f.name, dest))
            else:
                show_toast(f"「{f.name}」のデータを取得できませんでした", is_error=True)

        if resolved:
            ingest_files(resolved)

    file_picker = ft.FilePicker()  # Serviceとして生成時にページへ自動登録される

    # Send message / RAG query logic
    def send_message(e):
        query = query_input.value.strip()
        if not query:
            return
            
        # Clear input field
        query_input.value = ""
        query_input.disabled = True
        send_btn.disabled = True
        page.update()
        
        # 1. Add user message bubble
        chat_list.controls.append(
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("ユーザー", size=11, color="#A5B4FC", weight=ft.FontWeight.BOLD),
                        ft.Text(query, color="white", size=14)
                    ]),
                    bgcolor="#4F46E5",  # Vibrant indigo
                    padding=12,
                    border_radius=ft.BorderRadius.only(top_left=12, top_right=12, bottom_left=12, bottom_right=0),
                    width=480
                )
            ], alignment=ft.MainAxisAlignment.END)
        )
        page.update()
        
        # 2. Setup placeholders for AI streaming response
        thinking_text_control = ft.Text("", color="#94A3B8", size=13, italic=True)
        thinking_tile = ft.ExpansionTile(
            title=ft.Text("思考プロセスを表示中...", size=12, color="indigo300", italic=True),
            controls=[
                ft.Container(
                    content=thinking_text_control,
                    bgcolor="#1E222B",
                    padding=10,
                    border_radius=6,
                    margin=ft.Margin(10, 0, 10, 10)
                )
            ],
            visible=False,
            expanded=True
        )
        
        answer_markdown_control = ft.Markdown(
            "",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme="atom-one-dark"
        )
        
        sources_row = ft.Row(wrap=True, spacing=5)
        sources_container = ft.Container(
            content=ft.Column([
                ft.Divider(color="#2D313E", height=10),
                ft.Text("引用元ソース:", size=11, color="#6B7280", weight=ft.FontWeight.BOLD),
                sources_row
            ], spacing=5),
            visible=False
        )
        
        ai_bubble = ft.Container(
            content=ft.Column([
                ft.Text("ローカルAI (Gemma 4)", size=11, color="#10B981", weight=ft.FontWeight.BOLD),
                thinking_tile,
                answer_markdown_control,
                sources_container
            ], spacing=10),
            bgcolor="#1E222B",
            padding=15,
            border_radius=ft.BorderRadius.only(top_left=12, top_right=12, bottom_left=0, bottom_right=12),
            border=ft.Border(
                ft.BorderSide(1, "#2D313E"),
                ft.BorderSide(1, "#2D313E"),
                ft.BorderSide(1, "#2D313E"),
                ft.BorderSide(1, "#2D313E")
            ),
            width=600
        )
        
        chat_list.controls.append(
            ft.Row([ai_bubble], alignment=ft.MainAxisAlignment.START)
        )
        page.update()
        
        # Run streaming query in background
        def run_query():
            try:
                stream_generator = rag.query_rag_stream(
                    query, 
                    system_prompt=system_prompt_ref if system_prompt_ref else None,
                    top_k=top_k_ref,
                    llm_model=llm_model_ref
                )
                
                accumulated_text = ""
                
                for item in stream_generator:
                    if item["type"] == "sources":
                        # Populate citations
                        sources = item["sources"]
                        if sources:
                            sources_container.visible = True
                            for s in sources:
                                score_pct = s["score"] * 100
                                # Small pill for each source
                                sources_row.controls.append(
                                    ft.Container(
                                        content=ft.Text(f"{s['filename']} ({score_pct:.0f}%)", size=10, color="#E2E8F0"),
                                        bgcolor="#2D313E",
                                        padding=ft.Padding(10, 6, 10, 6),
                                        border_radius=15,
                                        tooltip=s["text"]  # Hover to read chunk snippet
                                    )
                                )
                            page.update()
                    
                    elif item["type"] == "token":
                        accumulated_text += item["content"]
                        
                        # Process thinking block vs normal answer
                        thinking_text, answer_text = parse_thinking_and_answer(accumulated_text)
                        
                        if thinking_text:
                            thinking_tile.visible = True
                            thinking_text_control.value = thinking_text
                        
                        answer_markdown_control.value = answer_text
                        page.update()
                        
            except Exception as ex:
                answer_markdown_control.value = f"**エラーが発生しました:**\n`{str(ex)}`"
                show_toast(f"クエリ処理中にエラー: {str(ex)}", is_error=True)
                
            finally:
                query_input.disabled = False
                send_btn.disabled = False
                page.update()
                query_input.focus()
                
        threading.Thread(target=run_query, daemon=True).start()

    # Configuration changes handlers
    def on_top_k_change(e):
        nonlocal top_k_ref
        top_k_ref = int(e.control.value)
        
    def on_sys_prompt_change(e):
        nonlocal system_prompt_ref
        system_prompt_ref = e.control.value.strip()

    def on_model_change(e):
        nonlocal llm_model_ref
        llm_model_ref = e.control.value.strip()

    # Layout Building
    sidebar = ft.Container(
        width=300,
        bgcolor="#0D0F12",  # Darker shade for sidebar
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MEMORY, color="indigo400", size=24),
                ft.Text("On-Premise RAG", size=18, weight=ft.FontWeight.BOLD, color="white")
            ], alignment=ft.MainAxisAlignment.START, spacing=10),
            ft.Text("完全ローカル・セキュアRAGシステム", size=10, color="#5C6479"),
            ft.Divider(color="#2D313E", height=20),
            
            # File Upload Section
            ft.Text("ドキュメント登録", size=12, weight=ft.FontWeight.BOLD, color="#94A3B8"),
            ft.Button(
                "ファイルを登録 (PDF/TXT/MD)",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=pick_and_register,
                style=ft.ButtonStyle(
                    bgcolor="indigo600",
                    color="white",
                    shape=ft.RoundedRectangleBorder(radius=8)
                ),
                width=260
            ),
            indexing_progress,
            ft.Divider(color="#2D313E", height=20),
            
            # Indexed Documents list
            ft.Row([
                ft.Text("登録済みファイル", size=12, weight=ft.FontWeight.BOLD, color="#94A3B8"),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_size=16, icon_color="#94A3B8", tooltip="更新", on_click=lambda _: refresh_document_list())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            doc_list_column,
            
            ft.Divider(color="#2D313E", height=20),
            
            # Expandable Settings
            ft.ExpansionTile(
                title=ft.Text("詳細設定", size=12, color="#94A3B8", weight=ft.FontWeight.BOLD),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text("モデル名 (Ollama)", size=10, color="#6B7280"),
                            ft.TextField(
                                value=llm_model_ref,
                                text_size=12,
                                dense=True,
                                bgcolor="#1E222B",
                                border_color="#3A3F50",
                                content_padding=10,
                                on_change=on_model_change
                            ),
                            ft.Text("類似ドキュメント取得数 (Top-K)", size=10, color="#6B7280"),
                            ft.Slider(
                                min=1, max=10, divisions=9,
                                value=top_k_ref,
                                label="{value}",
                                on_change=on_top_k_change,
                                active_color="indigo400"
                            ),
                            ft.Text("システムプロンプト", size=10, color="#6B7280"),
                            ft.TextField(
                                multiline=True,
                                min_lines=2,
                                max_lines=4,
                                hint_text="AIの振る舞いをカスタマイズ...",
                                bgcolor="#1E222B",
                                border_color="#3A3F50",
                                text_size=11,
                                on_change=on_sys_prompt_change
                            )
                        ], spacing=10),
                        padding=10
                    )
                ]
            )
        ], spacing=15)
    )

    main_chat_area = ft.Container(
        expand=True,
        bgcolor="#13151A",
        content=ft.Column([
            # Top Status Bar
            ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Container(width=8, height=8, bgcolor="green400", border_radius=4),
                        ft.Text("Ollama Connected (127.0.0.1:11434)", size=12, color="#94A3B8")
                    ], spacing=8),
                    ft.IconButton(
                        icon=ft.Icons.HIGHLIGHT_REMOVE,
                        icon_color="#6B7280",
                        tooltip="チャット履歴をクリア",
                        on_click=lambda _: (chat_list.controls.clear(), page.update())
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding(20, 15, 20, 15),
                border=ft.Border(bottom=ft.BorderSide(1, "#2D313E")),
                bgcolor="#181A20"
            ),
            
            # Chat List
            chat_list,
            
            # Input Area
            ft.Container(
                content=ft.Row([
                    query_input,
                    send_btn
                ], spacing=10),
                padding=20,
                border=ft.Border(top=ft.BorderSide(1, "#2D313E")),
                bgcolor="#181A20"
            )
        ], spacing=0)
    )

    # Initial document listing load
    refresh_document_list()

    # Overall page structure
    page.add(
        ft.Row([
            sidebar,
            ft.VerticalDivider(color="#2D313E", width=1),
            main_chat_area
        ], expand=True, spacing=0)
    )

# Bootstrapper to handle local vs browser tests
if __name__ == "__main__":
    # 日本語フォント等を配信するアセットディレクトリ（プロジェクトルート/assets）。
    # assets_dir は相対だと実行スクリプト基準で解決されるため絶対パスで渡す
    assets_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
    )
    if os.environ.get("FLET_VIEW") == "web":
        flet_port = int(os.environ.get("FLET_PORT", "8551"))
        print(f"Starting in Web-View mode for browser verification on port {flet_port}...")
        # デフォルトは 127.0.0.1（CORSエラー防止）。外部公開時のみ FLET_HOST="0.0.0.0" を指定する
        flet_host = os.environ.get("FLET_HOST", "127.0.0.1")
        ft.run(main, view=ft.AppView.WEB_BROWSER, host=flet_host, port=flet_port, no_cdn=True, assets_dir=assets_dir)
    else:
        print("Starting in Desktop Application mode...")
        ft.run(main, assets_dir=assets_dir)

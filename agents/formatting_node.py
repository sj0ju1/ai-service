import os
import traceback
import markdown as md
from playwright.sync_api import sync_playwright
from core.state import AgenticWorkflowState


def formatting_node(state: AgenticWorkflowState):
    """Playwright 기반 Markdown -> 세련된 Black & Grey 스타일 PDF 생성"""
    print("[Formatting Node] 고품격 PDF 문서 생성 중...")
    print("[Supervisor -> Formatting Node] 승인된 최종 초안을 전달받아 산출물을 생성합니다.")

    md_content = state["draft_work"]["current_draft"]
    if hasattr(md_content, "content"):
        md_content = md_content.content
    elif isinstance(md_content, dict):
        md_content = md_content.get("content", str(md_content))
    elif not isinstance(md_content, str):
        md_content = str(md_content)

    html_body = md.markdown(md_content, extensions=["tables", "fenced_code"])

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'AppleGothic', sans-serif;
                line-height: 1.7;
                padding: 3em;
                color: #333;
                background-color: #fff;
            }}

            h1 {{
                text-align: center;
                color: #000;
                font-size: 2.2em;
                margin-bottom: 1.5em;
                padding-bottom: 0.5em;
                border-bottom: 3px solid #333;
            }}
            h2 {{
                color: #2c3e50;
                font-size: 1.6em;
                margin-top: 1.5em;
                padding-left: 10px;
                border-left: 5px solid #2c3e50;
                background: #f8f9fa;
            }}
            h3 {{
                color: #444;
                font-size: 1.2em;
                border-bottom: 1px solid #ddd;
                padding-bottom: 3px;
                margin-top: 1.2em;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                font-size: 0.9em;
            }}
            th {{
                background-color: #2c3e50;
                color: white;
                font-weight: 700;
                padding: 12px;
                text-align: center !important;
            }}
            td {{
                border: 1px solid #eee;
                padding: 10px;
                text-align: left;
                vertical-align: top;
            }}
            tr:nth-child(even) {{
                background-color: #fcfcfc;
            }}

            blockquote {{
                border-left: 4px solid #7f8c8d;
                margin: 20px 0;
                padding: 15px;
                background: #f9f9f9;
                font-style: italic;
                color: #555;
            }}

            ul {{
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 8px;
            }}

            table, img, blockquote {{
                page-break-inside: avoid;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    output_pdf = os.path.join(output_dir, "ai-mini_output_3반_배수정+안가은.pdf")
    output_md = os.path.join(output_dir, "ai-mini_output_3반_배수정+안가은.md")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_template, wait_until="networkidle")
            page.pdf(
                path=output_pdf,
                format="A4",
                print_background=True,
                margin={"top": "60px", "right": "50px", "bottom": "60px", "left": "50px"},
            )
            browser.close()
        print(f"성공적으로 고품격 PDF가 생성되었습니다: {output_pdf}")
    except Exception as e:
        traceback.print_exc()
        print(f"⚠️PDF 변환 에러: {e}")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[Formatting Node -> User] Markdown 산출물 저장 완료: {output_md}")
    state["global_info"]["final_report"] = md_content
    state["global_info"]["workflow_status"] = "COMPLETED"
    return state

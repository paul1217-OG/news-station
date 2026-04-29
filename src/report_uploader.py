"""
report_uploader.py — 把 PDF 推到 GitHub repo 的 reports/ 資料夾
產生公開 URL：https://github.com/<owner>/<repo>/raw/main/reports/<filename>.pdf
"""
from __future__ import annotations
import base64
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Tuple


GITHUB_API = "https://api.github.com"


def upload_pdf_to_github(
    pdf_path: str,
    repo: str | None = None,
    token: str | None = None,
    branch: str = "main",
) -> Tuple[bool, str]:
    """
    把 PDF 推到 GitHub repo。
    回傳 (成功與否, URL 或錯誤訊息)
    """
    repo = repo or os.environ.get("GITHUB_REPO", "")
    token = token or os.environ.get("GITHUB_TOKEN", "")

    if not repo or not token:
        return False, "缺 GITHUB_REPO 或 GITHUB_TOKEN 環境變數"

    if not Path(pdf_path).exists():
        return False, f"找不到 PDF：{pdf_path}"

    # 讀檔 + base64
    pdf_bytes = Path(pdf_path).read_bytes()
    content_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    # 檔名：reports/2026-04-29.pdf
    today = datetime.now().strftime("%Y-%m-%d")
    target_path = f"reports/{today}.pdf"

    api_url = f"{GITHUB_API}/repos/{repo}/contents/{target_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # 先檢查檔案是否已存在（取得 sha 才能 update）
    check = requests.get(api_url, headers=headers, params={"ref": branch}, timeout=15)
    payload = {
        "message": f"Daily report {today}",
        "content": content_b64,
        "branch": branch,
    }
    if check.status_code == 200:
        # 已存在 → 需要 sha 來更新
        sha = check.json().get("sha")
        payload["sha"] = sha
        action = "更新"
    else:
        action = "建立"

    # PUT 上傳
    r = requests.put(api_url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        # 公開 URL
        public_url = f"https://github.com/{repo}/raw/{branch}/{target_path}"
        also_pdf_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{target_path}"
        print(f"📤 PDF 已{action} GitHub：{public_url}")
        return True, public_url
    else:
        return False, f"上傳失敗 {r.status_code}: {r.text[:200]}"


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "../output/daily_report.pdf"
    ok, msg = upload_pdf_to_github(pdf)
    print(("✅ " if ok else "❌ ") + msg)

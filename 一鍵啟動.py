"""
一鍵啟動腳本
============
功能：
1. 自動檢查 Python 版本
2. 自動安裝所有依賴
3. 互動式詢問 LINE Channel Access Token
4. 寫入 .env
5. 跑一次真實推播到你的 LINE

使用方式（在這個資料夾的終端機執行）：
    python 一鍵啟動.py
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ENV_FILE = ROOT / ".env"

def header(msg):
    print()
    print("=" * 60)
    print(f"  {msg}")
    print("=" * 60)

def step(n, total, msg):
    print(f"\n[{n}/{total}] ▶ {msg}")

def ok(msg):
    print(f"   ✅ {msg}")

def warn(msg):
    print(f"   ⚠️  {msg}")

def err(msg):
    print(f"   ❌ {msg}")

def fail(msg, code=1):
    err(msg)
    sys.exit(code)


def main():
    header("📰 每日新聞站｜一鍵啟動")

    TOTAL = 6

    # 1. Python 版本檢查
    step(1, TOTAL, "檢查 Python 版本")
    if sys.version_info < (3, 10):
        fail(f"需要 Python 3.10+，你目前是 {sys.version}")
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # 2. 安裝依賴
    step(2, TOTAL, "安裝必要套件（首次約 1～2 分鐘）")
    req = ROOT / "requirements.txt"
    if not req.exists():
        fail(f"找不到 {req}")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
            stderr=subprocess.STDOUT
        )
        ok("依賴安裝完成")
    except subprocess.CalledProcessError as e:
        warn("自動安裝失敗，嘗試加 --user 參數")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-q", "--user", "-r", str(req)]
            )
            ok("依賴安裝完成（user 模式）")
        except Exception:
            fail("套件安裝失敗，請手動執行：pip install -r requirements.txt")

    # 3. 詢問 LINE Token
    step(3, TOTAL, "輸入 LINE Channel Access Token")
    print("   ※ 從 https://developers.line.biz/console/ → Messaging API 分頁底部 Issue 取得")
    print("   ※ 貼上後按 Enter，輸入會被隱藏（避免肩窺）")
    print()

    # Windows 終端機 getpass 行為比較怪，用 input 但提示用戶小心
    try:
        import getpass
        token = getpass.getpass("   貼上你的 LINE Token：").strip()
    except Exception:
        token = input("   貼上你的 LINE Token（會顯示）：").strip()

    if len(token) < 50:
        fail(f"Token 太短（{len(token)} 字元），LINE token 通常 170+ 字元，請確認重貼")
    ok(f"Token 收到（{len(token)} 字元，前 6 字：{token[:6]}...）")

    # 4. 寫入 .env
    step(4, TOTAL, "寫入 .env 設定檔")
    env_content = f"""# 自動產生於 一鍵啟動.py
LINE_CHANNEL_ACCESS_TOKEN={token}
LINE_CHANNEL_SECRET=

# 暫時不用 OpenAI，使用內建 mock 摘要器
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

TOPIC_WEIGHTS_TW=40
TOPIC_WEIGHTS_US=25
TOPIC_WEIGHTS_ASIA=10
TOPIC_WEIGHTS_EU=5
TOPIC_WEIGHTS_INDUSTRY=15
TOPIC_WEIGHTS_MACRO=5

MAX_NEWS_ITEMS=8

# 第一次測試先設 false 直接送 LINE
DRY_RUN=false
"""
    ENV_FILE.write_text(env_content, encoding="utf-8")
    ok(f"已寫入 {ENV_FILE}")
    ok("（此檔已被 .gitignore 排除，不會上 git）")

    # 5. 確認送出
    step(5, TOTAL, "準備送出第一則真實 LINE 推播")
    print("   ⚠️  下一步會：")
    print("       1. 抓 RSS（沙盒環境可能抓不到，會用範例新聞 fallback）")
    print("       2. 用 mock 摘要器整理 8 條重點")
    print("       3. 產生圖文卡")
    print("       4. 廣播到你的 LINE 官方帳號所有好友")
    print()
    confirm = input("   確認送出？輸入 yes 繼續，其他鍵取消：").strip().lower()
    if confirm != "yes":
        warn("已取消（沒有送出 LINE）")
        sys.exit(0)

    # 6. 執行主程式
    step(6, TOTAL, "執行 main.py")
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "src" / "main.py")],
            cwd=str(ROOT / "src"),
            check=False,
        )
        if result.returncode == 0:
            print()
            header("🎉 完成！")
            print()
            print("  快去打開 LINE → 看你的官方帳號 → 應該收到一則 Flex Message")
            print()
            print("  📂 產出檔案在：")
            print(f"     {ROOT / 'output'}")
            print()
            print("  📞 沒收到訊息？檢查：")
            print("     1. 你有把自己的 LINE 加入這個官方帳號為好友嗎？")
            print("        (LINE 廣播 broadcast 只送給好友，不是自己後台帳號)")
            print("     2. main.py 上面有沒有 ✅ 推播成功？")
            print("     3. 看 output/flex_message.json 確認內容無誤")
        else:
            err(f"main.py 執行失敗 (exit code {result.returncode})")
            print("   把上面紅字錯誤訊息貼給我除錯")
    except KeyboardInterrupt:
        warn("使用者中斷")


if __name__ == "__main__":
    main()

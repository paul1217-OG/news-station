# v4 交付給網頁版 Claude 的 Prompt

> 把下方分隔線之間整段複製，貼給 https://claude.ai 網頁版（要有 Claude in Chrome 擴充套件 + Pro 帳號）。
> 它會用 Chrome 接手執行所有操作。

---

```
任務：幫我把財經早報專案升級到 v4 並上線。請用 Claude in Chrome 擴充套件直接操作我的瀏覽器。

==== 背景 ====
我有一個 GitHub repo: paul1217-OG/news-station
部署在 Railway，每日 7:30 抓財經新聞推播 LINE
目前是 v3，PDF 上傳因 PAT 權限問題失敗
我桌面 C:\Users\User\Desktop\news-station 有最新的 v4 程式碼，但還沒推上 GitHub

==== v4 升級內容（已寫好在桌面）====
1. ai_writer.py（新檔）：用 Gemini 把每篇新聞寫成 250~400 字繁中報導
2. mops_fetcher.py（新檔）：抓公開資訊觀測站重大訊息
3. config.yaml（已改）：加金融、餐飲、半導體、公發站優先
4. pdf_generator.py（已改）：手機友善報紙風格（800x1280 直式單欄）
5. main.py（已改）：整合上述模組
6. .env.example（已改）：加 GEMINI_API_KEY

==== 我要你做的（依序執行，每完成一步告訴我進度）====

【第 1 步：申請 Gemini API Key（免費）】
- 導航到 https://aistudio.google.com/apikey
- 用我的 Google 帳號登入（a12121122@gmail.com，已登入則跳過）
- 點「Create API Key」按鈕
- 選「Create API Key in new project」（如果沒專案的話）或選現有專案
- 把產生的 key（AIzaSy 開頭那串）複製到我的剪貼簿
- 不要顯示在 chat 視窗

【第 2 步：修復 GitHub PAT 權限】
v3 PDF 上傳失敗的錯誤：403 Resource not accessible by personal access token
表示舊 PAT 權限不夠。

- 導航到 https://github.com/settings/personal-access-tokens
- 找名稱含 "news-station" 的 token，點進去 → Delete
- 導航到 https://github.com/settings/personal-access-tokens/new
- 填寫：
  * Token name: news-station-v4
  * Expiration: 1 year
  * Resource owner: paul1217-OG
  * Repository access: Only select repositories
  * Select repositories: 勾選 news-station
- Permissions → Repository permissions → Contents: 改為 Read and write
- 其他權限保持 No access
- 滾到底點 Generate token
- 複製新 token 到剪貼簿（github_pat_ 開頭）

【第 3 步：到 Railway 更新環境變數】
- 導航到 https://railway.app/dashboard
- 點專案 cheerful-clarity
- 點中間 news-station 卡片
- 切到 Variables 分頁
- 用 Raw Editor 模式
- 確保有以下變數（更新或新增）：
  * GEMINI_API_KEY = <第 1 步的 Gemini key>
  * GITHUB_TOKEN = <第 2 步的新 PAT>
  * GITHUB_REPO = paul1217-OG/news-station（檢查是否已存在）
- 其他現有變數不要動（LINE_CHANNEL_ACCESS_TOKEN、TOPIC_WEIGHTS 等）
- 儲存

【第 4 步：把 v4 程式碼推到 GitHub】
方法 A：用 GitHub Desktop（如果使用者電腦有開）
- 提示使用者打開 GitHub Desktop
- 應該會看到一堆變更（v4 新增的檔案）
- Summary: "v4: Gemini AI 寫稿 + 公發站 + 報紙風格 PDF"
- 點 Commit to main → Push origin

方法 B：使用者沒開 GitHub Desktop，請告訴他：
"請打開 GitHub Desktop，會看到桌面 news-station 資料夾的變更，
 在 Summary 框寫 'v4 升級'，點 Commit to main，再點 Push origin。"

【第 5 步：等 Railway 部署完成】
- Railway 偵測到 git push 自動重新 build
- 切到 Deployments 分頁觀察
- 等到最新一筆變 Active（約 3-5 分鐘，因為有新 reportlab 等套件）

【第 6 步：手動觸發測試】
- 在 ACTIVE 那筆 deployment 旁邊點「···」(三點)
- 選 Redeploy
- 切到 Deploy Logs 觀察

【第 7 步：驗證 logs】
找以下關鍵字確認 v4 正確運作：
- "[1/6]" 開頭，到 "[6/6] 📤 LINE 推播" 結束（v4 是 6 階段）
- "🤖 使用 Gemini" 或 "✓ AI 寫稿完成"
- "✓ PDF 已上傳：https://github.com/..."
- "✅ 推播成功"

如果還是看到 "⚠️ PDF 上傳失敗：403" 表示 PAT 還是有問題，重做第 2 步。
如果 "⚠️ Gemini API 失敗" 表示 Gemini key 無效，重做第 1 步。

【第 8 步：驗證 LINE】
請我打開 LINE 看官方帳號，最新訊息封面卡上應該有：
- "📥 下載完整 PDF 報告" 按鈕
- 點下去能下載 PDF
- PDF 內容應該是「報紙風格」（米色底、紅頂條、大字標題、Drop Cap 首字、編輯導讀、引號等）

【第 9 步：驗證 GitHub reports/】
- 導航到 https://github.com/paul1217-OG/news-station/tree/main/reports
- 應該看到 2026-04-29.pdf（或當天日期）

==== 注意事項 ====
1. Gemini key 與 GitHub PAT 都是密碼級資料：
   - 處理時不要顯示在 chat 視窗
   - 處理完清除剪貼簿
2. 進行前先確認 Chrome 視窗有登入：
   - GitHub: paul1217-OG
   - Railway: 同 GitHub 帳號
   - Google AI Studio: a12121122@gmail.com
3. 任何一步報錯，停下來描述給我

請開始執行第 1 步。
```

---

## 📌 執行前你要確認

✅ Chrome 已登入：
- GitHub (paul1217-OG)
- Railway
- Google (a12121122@gmail.com)

✅ Claude in Chrome 擴充套件已安裝且 paired

✅ GitHub Desktop 桌面版已開（最後 push 階段需要）

## 🎁 這次升級你會得到

| Before (v3) | After (v4) |
|---|---|
| LINE 卡片：簡短英文翻譯 | LINE 卡片：完整繁中段落 |
| PDF：A4 橫式，Latin 字型 | PDF：手機直式報紙風格 |
| 內容：只有 RSS 來源 | + 公開資訊觀測站重大訊息 |
| 摘要：規則式 | Gemini AI 寫稿，每篇 250~400 字 |
| 編輯導讀：模板 | AI 撰寫，每天不同 |

## ⏱️ 全部執行完約 15 分鐘（網頁版 Claude 自動跑完）

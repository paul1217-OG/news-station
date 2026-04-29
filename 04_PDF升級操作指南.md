# 📄 PDF 報告升級操作指南｜v3 上線

> 本次升級：每日推播除了 LINE 圖卡，還會附帶**完整 PDF 報告連結**。內容包含每則新聞翻譯後全文 + 編輯小評 + 今日主旋律分析 + 明日值得關注。

---

## 🎁 你會得到的新功能

每日 LINE 推播的封面卡片會多一顆按鈕：
```
┌────────────────────┐
│  📰 每日財經早報    │
│  2026/04/29        │
│  ━━━━━━━━━         │
│  今日 8 大重點       │
│  → 滑右邊看每一則    │
│                    │
│ ┌────────────────┐ │
│ │ 📥 下載完整 PDF  │ │  ← 新增
│ └────────────────┘ │
│  繁體中文/含編輯小評│
└────────────────────┘
```

點下去會打開當日 PDF：
- **封面**：日期、今日主旋律、分類分布表
- **編輯部**：今日導讀（自動分析全日新聞）+ 明日值得關注事件
- **8 篇新聞**：每篇一頁，含繁中翻譯內文 + 編輯小評（規則式分析）+ 原文連結
- **背頁**：版權聲明、註腳

---

## 🛠️ 你需要做的（共 3 步驟）

### 步驟 1：申請 GitHub Personal Access Token（PAT）

PAT 是讓 Railway 上的程式有權限把每日 PDF 推到你的 GitHub repo 的鑰匙。

🔗 **點我開啟（直連申請頁）：** https://github.com/settings/personal-access-tokens/new

操作：
1. 確認上方分頁是「**Fine-grained tokens**」（建議用這種，比較安全）
2. **Token name**：`news-station-pdf-upload`
3. **Expiration**：選 1 year
4. **Resource owner**：你的個人帳號 `paul1217-OG`
5. **Repository access**：選「**Only select repositories**」→ 下拉選 `news-station`
6. **Permissions** 往下滾：
   - 找「**Repository permissions**」
   - 「**Contents**」這欄 → 從 `No access` 改成 `Read and write`
   - 其他權限**全部不用動**（保持 No access）
7. 滾到底點綠色「**Generate token**」
8. 出現的 `github_pat_xxxxx...` token **立刻複製存好**
   - ⚠️ 只會顯示這一次，關掉就拿不到了

---

### 步驟 2：把 PAT 加到 Railway 環境變數

🔗 https://railway.app → 你的 cheerful-clarity → news-station → **Variables**

新增 2 個變數：

| 變數名稱 | 值 |
|---|---|
| `GITHUB_TOKEN` | 貼上步驟 1 拿到的 `github_pat_xxxxx...` |
| `GITHUB_REPO` | `paul1217-OG/news-station` |

點 Save。Railway 會自動重新部署。

---

### 步驟 3：把新版本程式碼推到 GitHub

桌面 `news-station/` 資料夾已經有所有新檔案。打開 GitHub Desktop：

1. 你會看到一堆藍色 / 綠色變更：
   - 新檔：`src/pdf_generator.py`
   - 新檔：`src/editorial.py`
   - 新檔：`src/report_uploader.py`
   - 修改：`src/main.py`
   - 修改：`src/line_publisher.py`
   - 修改：`requirements.txt`
   - 修改：`.env.example`
   - 新檔：`04_PDF升級操作指南.md`（本檔）

2. 左下「Summary」框輸入：
   ```
   v3: 加入 PDF 報告 + 編輯部分析 + GitHub 上傳
   ```

3. 點藍色「**Commit to main**」

4. 點上方「**Push origin**」（或它會自動推）

5. Railway 偵測到 git push 後**自動重新 build + deploy**（2～3 分鐘）

---

## ✅ 驗證

### 方法 1：等明早 7:30 自然推播
明早起床看 LINE，封面卡應該多了「📥 下載完整 PDF 報告」按鈕。點下去能下載 PDF。

### 方法 2：手動觸發（速度版）
跟之前一樣：去 GitHub 把 `railway.json` 的 `cronSchedule` 從 `"30 23 * * *"` 改成 `"* * * * *"` → commit → 等 1 分鐘收 LINE → 立刻改回 `"30 23 * * *"`。

---

## 📂 PDF 會儲存在哪？

每日 PDF 自動 commit 到你的 repo：
```
https://github.com/paul1217-OG/news-station/tree/main/reports/
```

每天一個檔案：`reports/2026-04-29.pdf`、`reports/2026-04-30.pdf`...

歷史報告永久保留，未來想做「過去一週回顧」可以直接拉取。

---

## 🚨 常見問題

### Q1：PDF 沒出現在 LINE 卡片
- 檢查 Railway → news-station → Logs，找「PDF 已上傳」字樣
- 如果看到「⚠️ PDF 上傳失敗」→ GITHUB_TOKEN 可能填錯或過期
- 重新 issue 一個 PAT 並更新 Railway Variable

### Q2：點 PDF 連結瀏覽器顯示 404
- 第一次 Railway 跑完後，到 https://github.com/paul1217-OG/news-station/tree/main/reports 看檔案有沒有真的進來
- 如果沒有 → GITHUB_TOKEN 權限不夠，回步驟 1 確認 Contents = Read and write

### Q3：PDF 中文是方框
- 不會發生在 Railway 上（Dockerfile 已裝 fonts-noto-cjk）
- 如果發生 → 檢查 Build Logs 確認 `apt install fonts-noto-cjk` 有跑

### Q4：reports/ 資料夾會不會把 repo 撐爆
- 每日 PDF 約 100-300 KB
- 一年 = 365 個檔案 = 約 70 MB（GitHub 免費上限 1 GB）
- 完全不用擔心，可以跑很多年

### Q5：PDF 內容感覺有點「機器」，沒有 AI 那種流暢度
- 是的，目前用規則式分析 + Google Translate 免費版
- 升級路徑：之後加 OpenAI 後，可改用 GPT-4o-mini 重寫每則新聞 + 產生編輯導讀，品質會像真人寫的
- 成本：USD 0.5/月

---

## 🔄 接下來的選項

完成上述 3 步驟後，你的系統會有完整功能。再來想優化品質：

### 加 OpenAI（強烈建議下一步做）
- 免費版 Google Translate 翻譯品質中等，遇到專有名詞會卡
- GPT-4o-mini 翻譯 + 改寫，品質像專業財經編輯
- 月成本：< NT$30
- 操作：5 分鐘
- 詳見：[03_上線完成_日常維護手冊.md](./03_上線完成_日常維護手冊.md) 的 Phase 3 段落

### 加更多 RSS 來源
- 編輯 `config.yaml` 新增來源
- 例如：MoneyDJ、StockFeel、財訊、商業周刊

### 自訂 PDF 視覺
- 編輯 `src/pdf_generator.py`
- 改 `INK_900`、`GOLD` 等顏色變數
- 改 `_styles()` 內各文字大小

---

**完成 3 步驟後告訴我「v3 上線了」，我幫你驗證 + 一起確認 PDF 出現在 LINE 卡片中。**

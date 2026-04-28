# Railway 雲端部署手把手｜每日 7:30 自動推播

> Railway = 比 VPS 簡單 10 倍的雲端服務。免註冊信用卡可用 30 天免費額度，足夠每日推播 1 次跑半年。
> 完成後你電腦關機也會推播，徹底「無人看管」。

---

## 為什麼選 Railway？（vs VPS / GitHub Actions）

| 比較 | Railway | VPS（DigitalOcean等） | GitHub Actions |
|---|---|---|---|
| 設定難度 | 簡單（拉 GitHub repo） | 需要 SSH、Linux 技能 | 簡單但限制多 |
| 月費 | 免費 5 美元額度（夠用） | NT$200~600 | 免費但每月 2,000 分鐘上限 |
| 排程 cron | ✅ 內建 | 需自己設 | ✅ 內建 |
| 中文字型 | ✅ Dockerfile 已寫好 | 需自己 apt install | ⚠️ 每次都要重裝 |
| 環境變數 | ✅ 介面填寫 | ✅ ssh 寫 .env | ✅ Secrets |
| **推薦度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 部署前 3 個前置動作（你要先做）

### 動作 1：把 news_station 上傳到 GitHub

Railway 是從 GitHub 自動拉你的程式碼。所以你要先有一個 GitHub 帳號 + 一個 repo。

🔗 **GitHub 註冊：** https://github.com/signup（免費）

#### A. 沒裝過 Git？（最簡單路線：用 GitHub Desktop）

1. 下載 GitHub Desktop：https://desktop.github.com/
2. 安裝後登入你的 GitHub 帳號
3. 開 GitHub Desktop → File → New Repository
   - Name: `news-station`
   - Local path: 選到 `C:\Users\User\Desktop`（**不要選 news_station 內**）
   - Initialize with README：不勾
   - 點 Create Repository
4. 它會建一個新資料夾 `news-station`，**把 news_station 裡所有檔案剪下貼到這個新資料夾裡**
5. 回到 GitHub Desktop → 你會看到所有檔案 → 寫 commit 訊息「Initial commit」→ 點 Commit
6. 點右上「Publish repository」→ 取消勾「Keep this code private」(讓 Railway 能讀)，或保持私有但要在 Railway 連結時授權
7. 完成後你的 repo 會在 https://github.com/你的帳號/news-station

#### B. 已會用 Git 的話

```bash
cd C:\Users\User\Desktop\news_station
git init
git add .
git commit -m "Initial commit"
gh repo create news-station --public --source=. --push
```

**⚠️ 確認：你的 .gitignore 要包含 .env**（已預設好）。確認 .env 沒進 git：
```bash
git ls-files | grep .env
# 應該只看到 .env.example，不能看到 .env
```

---

### 動作 2：註冊 Railway 帳號

🔗 **點我開啟：** https://railway.app/login

1. 點「**Login with GitHub**」（用 GitHub 登入最方便）
2. 授權 Railway 讀取你的 GitHub
3. 完成

---

### 動作 3：手上要有 LINE Channel Access Token

之前已經拿到了，準備好待會貼。

---

## 🚀 開始部署（4 步驟，約 10 分鐘）

### 步驟 1：在 Railway 建立新專案

1. 登入後點右上角「**+ New Project**」
2. 選「**Deploy from GitHub repo**」
3. 第一次需要授權 Railway 讀取你的 GitHub repo（點 Configure GitHub App）
4. 選你剛建立的 `news-station` repo
5. Railway 會自動偵測到 Dockerfile，開始第一次 build（約 2~3 分鐘）

### 步驟 2：設定環境變數

第一次 build 失敗很正常，因為還沒貼 token。

1. 進入 Project → 點該 service（一般叫 `news-station`）
2. 切到「**Variables**」分頁
3. 點「**+ New Variable**」一個一個加：

| 變數名 | 值 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | （貼你的 token） |
| `OPENAI_API_KEY` | 留空（之後再加） |
| `DRY_RUN` | `false` |
| `TOPIC_WEIGHTS_TW` | `40` |
| `TOPIC_WEIGHTS_US` | `25` |
| `TOPIC_WEIGHTS_ASIA` | `10` |
| `TOPIC_WEIGHTS_EU` | `5` |
| `TOPIC_WEIGHTS_INDUSTRY` | `15` |
| `TOPIC_WEIGHTS_MACRO` | `5` |
| `MAX_NEWS_ITEMS` | `8` |
| `USE_ONLINE_TRANSLATE` | `true` |
| `TZ` | `Asia/Taipei` |

點「Save」→ Railway 會自動重新部署。

### 步驟 3：設定 Cron Schedule（每日 7:30）

1. 進入 service 的 「**Settings**」分頁
2. 找「**Cron Schedule**」（如果沒看到，可能在「Service Settings」展開區）
3. 填入：`30 23 * * *`
   - 注意：Railway 預設 UTC 時間。台灣 7:30 = UTC 23:30 前一日
   - 如果你的 service 已設 TZ=Asia/Taipei 環境變數，可改填 `30 7 * * *`
4. 「**Restart Policy**」選 `NEVER`（這是 cron 任務，不該一直重啟）
5. 點 Apply

### 步驟 4：手動觸發一次驗證

在部署成功後，先別等明天 7:30，立刻觸發一次：

1. 進入 service → 「**Deployments**」分頁
2. 找最新的部署 → 右上「**...**」選單 → 「**Restart**」
3. 它會立刻跑一次 `python src/main.py`
4. 切到「**Logs**」分頁觀察執行過程
5. 你的 LINE 應該收到一則訊息

---

## ✅ 驗證清單

- [ ] GitHub repo 建立成功，可以在網頁看到所有檔案
- [ ] `.env` **沒有**被推上 GitHub（檢查 repo 的檔案列表，不應有 .env）
- [ ] Railway 顯示綠色「Deploy successful」
- [ ] Railway Variables 包含 LINE_CHANNEL_ACCESS_TOKEN
- [ ] Cron Schedule 顯示 `30 23 * * *`
- [ ] 手動觸發後 LINE 收到訊息
- [ ] 隔天早上 7:30 收到自動推播

---

## 💰 成本預估

Railway 免費額度：每月 USD 5（約 NT$160），夠用：
- 每次執行約 1～2 分鐘 × 30 天 = 60 分鐘執行時間
- 30 個 build × 各約 30MB 流量 = 1GB
- 每月實際花費 < USD 1

**幾乎等於免費。**

---

## 🚨 疑難排解

### Q1：「Deploy failed - Dockerfile not found」
A：檢查 `Dockerfile` 是否在 repo 根目錄、是否被 commit 上來。

### Q2：「Module 'feedparser' not found」
A：requirements.txt 沒有正確 commit，Railway 沒裝套件。重新 push 一次。

### Q3：Cron 沒在 7:30 跑
A：檢查兩件事：
1. Railway 的 schedule 用 **UTC**。台灣 = UTC+8，所以早上 7:30 = UTC 23:30 前一日 → cron `30 23 * * *`
2. 確認 `Restart Policy` = NEVER（如果 ON_FAILURE 可能會狂跑）

### Q4：「LINE 401 Unauthorized」
A：Token 過期或填錯。回 LINE Developers Console 重新 issue 一次，更新 Railway Variable。

### Q5：訊息收到但圖卡是空白方框
A：Dockerfile 沒裝中文字型。確認 Dockerfile 第一段有 `fonts-noto-cjk`。

### Q6：怎麼看 Logs？
A：Railway service → Deployments → 點任一次 deploy → Logs 分頁。每次 cron 執行都會留 log 至少 7 天。

---

## 🔧 後續維護

### 改新聞來源 / 主題權重
1. 編輯本機 `config.yaml` 或 .env
2. `git add . && git commit -m "update sources" && git push`
3. Railway 自動重新部署

### 看訂閱者數
LINE Manager → 主頁 → 看好友數

### 升級訊息額度
LINE OA 後台 → 升級到「低用量方案」NT$200/月（4,000 則訊息）

### 加 OpenAI 真 AI 摘要
1. 註冊 OpenAI、加值 USD 5、取得 key
2. Railway Variables → 把 OPENAI_API_KEY 填進去
3. 重新部署，下次推播就會用真 AI

---

## 📞 需要幫忙時

1. 把 Railway Logs 整段貼給我
2. 把錯誤訊息原文貼給我（不要截圖，貼文字才能搜尋）
3. 不確定填什麼直接問

我會接著陪你跑完每一步。

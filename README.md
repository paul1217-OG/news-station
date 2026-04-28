# 每日新聞站 LINE 推播系統

每天台灣時間 7:30 自動向 LINE 官方帳號訂閱者推播：
- 國際財經新聞
- 台股／美股／亞股／歐股動向
- 重點產業消息
- 公開資訊觀測站重大訊息
- AI 摘要 + 圖文卡片

---

## 📦 專案結構

```
news_station/
├── README.md                      ← 本檔
├── 01_申請操作清單.md             ← 你要先完成的事（5 個申請步驟）
├── 每日新聞站_執行藍圖.md        ← 完整系統規劃書
├── requirements.txt               ← Python 依賴
├── .env.example                   ← 環境變數範本
├── config.yaml                    ← 新聞來源設定
├── src/
│   ├── main.py                    ← 主程式入口（每天 7:30 跑這個）
│   ├── news_collector.py          ← 多源 RSS 並行抓取 + 去重
│   ├── ai_summarizer.py           ← OpenAI GPT-4o-mini 摘要
│   ├── image_generator.py         ← Pillow 產生新聞卡圖片
│   └── line_publisher.py          ← LINE Messaging API 推播
└── output/                        ← 每日產出（JSON + 圖片）
    ├── raw_news.json
    ├── summarized.json
    ├── flex_message.json
    └── cards/
        ├── 00_cover.jpg           封面卡
        ├── 01_card.jpg ~ 08_card.jpg
```

---

## 🚀 快速開始（你的 VPS 上跑）

### 1. 系統依賴（Ubuntu 22.04）
```bash
# 中文字型 + emoji 字型（必裝，否則中文會變方框）
sudo apt update && sudo apt install -y \
    python3-pip \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fonts-noto-cjk-extra

# Python 套件
cd news_station
pip install -r requirements.txt
```

### 2. 設定環境變數
```bash
cp .env.example .env
nano .env
# 填入：
#   LINE_CHANNEL_ACCESS_TOKEN=你的 token
#   OPENAI_API_KEY=sk-xxxxxx
#   DRY_RUN=false   ← 正式上線時設為 false
```

### 3. 第一次測試（dry-run，不送 LINE）
```bash
cd src
python main.py
# 看 output/flex_message.json 確認內容
# 看 output/cards/*.jpg 確認圖片
```

### 4. 正式推播測試
```bash
# 在 .env 把 DRY_RUN=false
cd src
python main.py
# 你的 LINE 應該會收到測試訊息
```

### 5. 設定每日 7:30 自動執行
```bash
crontab -e
# 加入這行（台灣時間 7:30 = UTC 23:30 前一日）
30 23 * * * cd /home/你/news_station/src && /usr/bin/python3 main.py >> /var/log/news_station.log 2>&1
# 注意：如果你 VPS 時區是 Asia/Taipei，直接寫：
# 30 7 * * * cd /home/你/news_station/src && /usr/bin/python3 main.py >> /var/log/news_station.log 2>&1
```

確認時區：
```bash
timedatectl
# 改成台北時區：
sudo timedatectl set-timezone Asia/Taipei
```

---

## 🔑 必要的 5 個密鑰／帳號

| # | 服務 | 取得位置 | 寫到哪裡 |
|---|---|---|---|
| 1 | LINE Channel Access Token | https://developers.line.biz/console/ | `.env` 的 `LINE_CHANNEL_ACCESS_TOKEN` |
| 2 | LINE Channel Secret | 同上 | `.env` 的 `LINE_CHANNEL_SECRET` |
| 3 | OpenAI API Key | https://platform.openai.com/api-keys | `.env` 的 `OPENAI_API_KEY` |
| 4 | VPS 帳號（自己選） | DigitalOcean / Linode / Vultr | n/a |
| 5 | 公開資訊觀測站 OpenAPI | 免註冊 | 程式直接呼叫 |

詳細申請步驟見 `01_申請操作清單.md`。

---

## 🛡️ 安全與穩定性建議

1. **API Key 不要進 git**：`.env` 檔已被列入 `.gitignore`
2. **設置額度警報**：OpenAI dashboard 設 monthly limit USD 10
3. **失敗重試**：若 RSS 抓不到、AI 失敗，main.py 會 fallback 到 mock 不會中斷
4. **日誌監控**：cron 把 stderr 寫入 `/var/log/news_station.log`，每週檢查一次
5. **訂閱者管理**：LINE OA 後台可看好友數，超過免費額度前升級

---

## 🔧 常用維護指令

```bash
# 看今日推播內容
cat output/flex_message.json | python3 -m json.tool | less

# 重新跑（不發 LINE，測試用）
DRY_RUN=true python3 src/main.py

# 看抓回來的原始新聞
cat output/raw_news.json | python3 -m json.tool | head -50

# 強制使用 mock（不呼叫 OpenAI 省錢測試）
unset OPENAI_API_KEY && python3 src/main.py
```

---

## 📈 下一步可加功能（未來迭代）

- [ ] 訂閱者分眾：依 LINE Tag 分類（散戶／法人／產業偏好）
- [ ] 互動式查詢：好友傳「台積電」就回該股最新新聞
- [ ] 雲端 RSS 快取：用 Cloudflare Workers 加速 + 反爬蟲
- [ ] Canva Template API 整合：更精緻的視覺
- [ ] 週報 / 月報自動生成
- [ ] NotebookLM 跨期分析（手動驅動，每週 1 次）

---

## 🐛 疑難排解

**Q: 為什麼中文變方框？**  
A: VPS 沒裝中文字型。執行 `sudo apt install fonts-noto-cjk fonts-noto-color-emoji`

**Q: RSS 抓不到？**  
A: 對方可能擋 IP 或改了 feed URL。查 `config.yaml` 把死掉的源換掉。

**Q: LINE 推播失敗 400 / 401？**  
A: 401 = token 無效，重新到 LINE Developers 重發 token。400 = Flex JSON 格式錯，貼到 LINE Flex Simulator https://developers.line.biz/flex-simulator/ 除錯。

**Q: 想換成 Claude API 不用 OpenAI？**  
A: 把 `ai_summarizer.py` 的 `summarize_with_openai` 改成 anthropic SDK，邏輯一樣。Claude 3.5 Haiku 比 GPT-4o-mini 還便宜。

**Q: 每月 LINE 訊息超過免費額度怎麼辦？**  
A: LINE OA 後台 → 升級到「低用量方案」NT$200/月（4,000 則）或「中用量」NT$800/月（25,000 則）。

---

## 📞 在哪裡求救

- LINE Messaging API 文件：https://developers.line.biz/en/docs/messaging-api/
- OpenAI API 文件：https://platform.openai.com/docs
- LINE Flex Simulator（除錯神器）：https://developers.line.biz/flex-simulator/

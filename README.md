# Social Forwarder

*追蹤社群平台上的創作者並自動發送最新貼文至 Telegram 頻道的小工具。*

## 核心功能

- **穩定追蹤**：具備自動切換來源節點的機制，即使單一伺服器故障也能確保追蹤不中斷。
- **直覺體驗**：自動將內容連結還原為 X.com 官方格式，點擊後可直接開啟官方 App 或網頁。
- **頻道管理**：支援 Telegram 的「討論主題 (Topics)」，將來源貼文精確發送到特定的主題區。
- **零重複通知**：內建判別系統，確保每則貼文只會推送一次，絕不洗板。
- **多帳號監控**：支援同時追蹤多個 X 帳號，將所有分散的資訊流集中在同一個 Telegram 頻道中。

## 安裝

1. 安裝 Python 3.9+
2. 安裝依賴：

```bash
pip install -r requirements.txt
```

## 環境變數

請在專案根目錄建立 `.env`（可由 `.env.example` 複製）：

```bash
TG_BOT_TOKEN='your_telegram_bot_token'
```

## 設定檔 (config.json)

`config.json` 包含：

- `accounts`：要追蹤的 X/Twitter 帳號列表。
- `nitter_instances`：可用的 Nitter 實例列表（用於分散壓力與冗餘）。
- `check_interval`：檢查間隔（秒）。
- `telegram`：目標頻道 ID 與主題 ID。

## 歷史紀錄 (processed_posts.json)

`processed_posts.json` 用於記錄每個帳號最後一次發送的貼文 ID，以確保貼文不會重複發送。

如果你需要從其他地方轉移紀錄或手動設定起始點，可以參考 `processed_posts.json.example`：

1. 複製 `processed_posts.json.example` 並重新命名為 `processed_posts.json`。
2. 填入帳號名稱與對應的貼文 ID (Snowflake ID)。

## 啟動

```bash
python main.py
```

## 貢獻與反饋

如果你有功能建議，歡迎隨時提出！

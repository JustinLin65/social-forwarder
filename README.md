# Social Forwarder

*追蹤社群平台（如 X/Twitter）上的創作者並自動發送最新貼文至 Telegram 頻道的小工具。*

## 核心功能

- **媒體支援**：自動擷取推文中的**圖片與影片**。支援多圖混合發送 (Media Group)，讓 Telegram 上的內容與原貼文一樣豐富。
- **穩定追蹤**：具備自動切換來源節點 (Nitter Instances) 的機制，即使單一伺服器故障也能確保追蹤不中斷。
- **直覺體驗**：自動將 Nitter 連結還原為 `x.com` 官方格式，點擊後可直接開啟官方 App 或網頁。
- **靈活配置**：可自由開關連結、文字、預覽圖的顯示，適配不同風格的推送頻道。
- **頻道管理**：支援 Telegram 的「討論主題 (Topics)」，將來源貼文精確發送到特定的主題區。
- **零重複通知**：內建判別系統與本地資料庫，確保每則貼文只會推送一次。
- **長文字處理**：自動截斷超過 Telegram 限制的長文字，確保訊息發送成功。

## 安裝

1. 安裝 Python 3.9+
2. 下載專案並安裝依賴：

```bash
pip install -r requirements.txt
```

## 環境變數

請在專案根目錄建立 `.env`（可由 `.env.example` 複製）：

```bash
TG_BOT_TOKEN='your_telegram_bot_token'
```

## 設定檔 (config.json)

建立 `config.json`（可由 `config.json.example` 複製）：

- `debug`: (Boolean) 是否開啟偵錯模式，顯示詳細抓取日誌。
- `check_interval`: (Integer) 檢查間隔（秒）。
- `accounts`: (Array) 要追蹤的 X/Twitter 帳號列表（不含 @）。
- `nitter_instances`: (Array) 可用的 Nitter 實例列表，建議填入多個以維持冗餘。
- `telegram`:
  - `chat_id`: 目標群組或頻道 ID。
  - `topic_id`: (Optional) 討論主題 ID，若無則填 `null`。
  - `show_link`: 是否發送原始貼文連結。
  - `show_text`: 是否發送貼文內容。
  - `show_preview`: 是否顯示網頁連結預覽。

## 歷史紀錄 (processed_posts.json)

程式會自動產生此檔案，記錄每個帳號最後一次發送的貼文 ID。若需手動設定起始點，可參考 `processed_posts.json.example` 的格式。

## 啟動

```bash
python main.py
```

## 貢獻與反饋

如果你有功能建議或發現問題，歡迎隨時提出！

# Social Forwarder

*追蹤社群平台（如 X/Twitter）上的創作者並自動發送最新貼文至 Telegram 頻道，支援 AI 自動處理。*

## 核心功能

- **AI 自動處理 (Gemini)**：可對貼文內容進行**自動翻譯、摘要或格式化**。
    - **穩定回退機制**：若 AI 處理失敗（如 API 額度用盡或網路問題），系統將自動發送原文，並標註 `(API調用失敗)` 提醒。
    - 具備指數退避重試機制，確保高成功率。
- **媒體支援**：自動擷取推文中的**圖片與影片**。支援多媒體混合發送 (Media Group)，還原最真實的貼文內容。
- **穩定追蹤**：具備自動切換來源節點 (Nitter Instances) 機制，多節點冗餘設計，確保服務不中斷。
- **連結還原**：自動將連結還原為官方 `x.com` 格式。
- **靈活配置**：支援頻道討論主題 (Topics)，並可自定義訊息組成（連結、文字、預覽圖）。
- **健壯性**：內建自動截斷與錯誤處理機制，確保在大流量或異常環境下穩定運行。

## 安裝

1. 安裝 Python 3.9+
2. 下載專案並安裝依賴：

```bash
pip install -r requirements.txt
```

## 環境變數

請在根目錄建立 `.env`（參考 `.env.example`）：

```bash
TG_BOT_TOKEN='your_telegram_bot_token'
GEMINI_API_KEY='your_gemini_api_key' # 若不使用 AI 功能可留空
```

## 設定檔 (config.json)

建立 `config.json`（參考 `config.json.example`）：

- `ai`:
  - `enabled`: (Boolean) 是否啟用 AI 處理。
  - `model`: (String) Gemini 模型版本（如 `gemini-1.5-flash`）。
  - `prompt`: (String) 要交給 AI 的指令（如「請翻譯成中文：」）。
- `debug`: (Boolean) 開啟則顯示詳細抓取紀錄。
- `check_interval`: (Integer) 輪詢間隔（秒）。
- `accounts`: (Array) 追蹤帳號清單。
- `nitter_instances`: (Array) Nitter RSS 來源清單。
- `telegram`:
  - `chat_id`: 目標頻道 ID。
  - `topic_id`: (Optional) 討論主題 ID。
  - `show_link`/`show_text`/`show_preview`: 顯示開關。

## 啟動

```bash
python main.py
```

## 常見問題 (Troubleshooting)

- **AI 訊息出現「(API調用失敗)」**：
    - 請檢查 `.env` 中的 `GEMINI_API_KEY` 是否正確。
    - 檢查 Google AI Studio 的額度是否用盡。
    - 若該貼文內容違反 AI 安全性原則（如涉及敏感內容），API 可能會拒絕處理。
- **無法獲取貼文或顯示「所有實例無法存取」**：
    - Nitter 公共實例不穩定是常見現象，建議在 `config.json` 的 `nitter_instances` 中多加入幾個可用的實例。
    - 您可以參考 [Nitter Instances List](https://github.com/zedeus/nitter/wiki/Instances) 獲取最新清單。
- **Telegram 沒收到訊息**：
    - 檢查 `chat_id` 是否正確（頻道 ID 通常以 `-100` 開頭）。
    - 確保 Bot 已被加入該頻道並擁有發送訊息的權限。

## 貢獻與反饋

如有任何建議，歡迎隨時提出！

# Changelog

本專案的所有顯著變更將記錄在此檔案中。
格式參考自 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

## [1.1.0] - 2026-04-23

### Added

- **AI 處理功能**：整合 Google Gemini API。
    - 支援自動翻譯、總結或改寫貼文內容。
    - 內建指數退避 (Exponential Backoff) 重試機制，應對 API 速率限制 (429)。
    - 可自定義 AI Prompt 與模型版本。
- **配置更新**：新增 `ai` 配置區塊。

## [1.0.0] - 2026-04-22

### Added

- **媒體支援**：自動擷取推文中的圖片與影片（支援多圖/影片混合發送）。
- **進階配置**：新增 `show_link`、`show_text`、`show_preview` 開關，可自定義 Telegram 訊息組成。
- **偵錯模式**：新增 `debug` 開關，方便排查 RSS 獲取問題。
- **文字處理**：新增自動截斷功能，確保訊息符合 Telegram API 長度限制。

## [0.1.0] - 2026-04

### Added

- **初始版本發佈**：支援從 Nitter RSS 抓取 X/Twitter 貼文。
- **Telegram 推送**：支援傳送至特定頻道與 Topic。
- **本地資料庫**：利用 JSON 檔案追蹤已處理贴文。

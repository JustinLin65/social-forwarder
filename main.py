import os
import time
import json
import feedparser
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse

# 1. 初始化與讀取配置
load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

CONFIG_FILE = "config.json"
DB_FILE = "processed_posts.json"

def load_config():
    """載入 JSON 配置文件"""
    if not os.path.exists(CONFIG_FILE):
        print(f"錯誤: 找不到 {CONFIG_FILE}")
        exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_db():
    """載入已處理過的貼文紀錄"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    """儲存紀錄"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def convert_to_x_link(nitter_url):
    """將 Nitter 連結轉換為 X.com 連結"""
    try:
        parsed = urlparse(nitter_url)
        # 取得路徑部分 (例如 /VitalikButerin/status/12345)
        # 並確保移除末尾的 #m 
        path = parsed.path
        return f"https://x.com{path}"
    except Exception:
        return nitter_url

def send_telegram(config, text):
    """發送訊息至 Telegram (支援 Topic ID)"""
    tg_conf = config.get("telegram", {})
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": tg_conf.get("chat_id"),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": tg_conf.get("disable_preview", False)
    }

    # 如果有設定 Topic ID (message_thread_id)
    if tg_conf.get("topic_id"):
        payload["message_thread_id"] = tg_conf.get("topic_id")

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"TG 發送失敗 (HTTP {response.status_code}): {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram 連線失敗: {e}")
        return False

def fetch_from_nitter(account, instances):
    """輪詢 Nitter 實例獲取數據"""
    for instance in instances:
        rss_url = f"{instance.rstrip('/')}/{account}/rss"
        try:
            feed = feedparser.parse(rss_url)
            if feed.entries:
                return feed.entries
            else:
                print(f"[-] 實例 {instance} 無法取得 @{account} 內容")
        except Exception as e:
            print(f"[-] 實例 {instance} 出錯: {e}")
    return None

def main():
    print("=== X Monitor 服務啟動 ===")
    processed_data = load_db()

    while True:
        config = load_config()
        accounts = config.get("accounts", [])
        instances = config.get("nitter_instances", [])
        interval = config.get("check_interval", 600)

        for account in accounts:
            entries = fetch_from_nitter(account, instances)
            
            if not entries:
                print(f"[!] 跳過 @{account}，所有實例皆無法存取。")
                continue

            new_posts = []
            for entry in entries[:5]:
                post_id = entry.id
                title = entry.title
                nitter_link = entry.link

                # 檢查是否已處理
                if account in processed_data and processed_data[account] == post_id:
                    break 

                # 忽略轉發貼文
                if title.startswith("RT by") or title.startswith("RT @"):
                    continue

                # 轉換連結：將 nitter.net/... 轉為 x.com/...
                x_link = convert_to_x_link(nitter_link)
                new_posts.append((post_id, x_link))

            # 倒序發送
            for p_id, p_link in reversed(new_posts):
                print(f"[+] 發現新推文 @{account}: {p_link}")
                message = f"<b>來自 @{account} 的新推文</b>\n\n{p_link}"
                
                if send_telegram(config, message):
                    processed_data[account] = p_id
                    save_db(processed_data)
                    time.sleep(2)

        print(f"[*] 檢查完畢，等候 {interval} 秒...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
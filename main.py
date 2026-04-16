import os
import asyncio
import json
import aiohttp
import feedparser
import time
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

# ==================== 配置與路徑 ====================
CONFIG_FILE = "config.json"
DB_FILE = "processed_posts.json"

# 全域變數
PROCESSED_DATA = {}
DEBUG_MODE = False

# ==================== 核心邏輯 ====================

def load_all_configs():
    """載入配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] 讀取 {CONFIG_FILE} 失敗: {e}")
            exit(1)
    else:
        print(f"[!] 警告：找不到 {CONFIG_FILE}")
        exit(1)

def load_db():
    """載入已處理紀錄"""
    global PROCESSED_DATA
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                PROCESSED_DATA = json.load(f)
                print(f"[V] 已載入歷史紀錄：{len(PROCESSED_DATA)} 個帳號")
        except Exception as e:
            print(f"[!] 讀取 {DB_FILE} 失敗: {e}")
    else:
        print(f"[*] 建立新的歷史紀錄庫")

def save_db():
    """儲存紀錄"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(PROCESSED_DATA, f, indent=2)
    except Exception as e:
        print(f"[!] 儲存 {DB_FILE} 失敗: {e}")

def convert_to_x_link(nitter_url):
    """將 Nitter 連結轉換為 X.com 連結"""
    try:
        parsed = urlparse(nitter_url)
        path = parsed.path
        return f"https://x.com{path}"
    except Exception:
        return nitter_url

async def send_telegram(session, config, text):
    """發送訊息至 Telegram (非同步)"""
    tg_conf = config.get("telegram", {})
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": tg_conf.get("chat_id"),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": tg_conf.get("disable_preview", False)
    }
    
    if tg_conf.get("topic_id"):
        payload["message_thread_id"] = tg_conf.get("topic_id")

    try:
        async with session.post(url, json=payload, timeout=15) as resp:
            if resp.status != 200:
                print(f"   [X] TG 發送失敗 (HTTP {resp.status}): {await resp.text()}")
            return resp.status == 200
    except Exception as e:
        print(f"   [!] Telegram 發送異常: {e}")
        return False

async def fetch_rss(session, url):
    """獲取並解析 RSS 內容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        async with session.get(url, headers=headers, timeout=20) as resp:
            if resp.status == 200:
                content = await resp.text()
                return feedparser.parse(content)
            return None
    except Exception as e:
        if DEBUG_MODE:
            print(f"   [!] RSS 獲取失敗 ({url}): {e}")
        return None

async def check_account(session, account, instances, config):
    """檢查單個帳號的新推文"""
    global PROCESSED_DATA
    
    for instance in instances:
        rss_url = f"{instance.rstrip('/')}/{account}/rss"
        feed = await fetch_rss(session, rss_url)
        
        if feed and feed.entries:
            new_posts = []
            for entry in feed.entries[:10]: # 檢查最近 10 則
                post_id = entry.id
                title = getattr(entry, 'title', '')
                link = getattr(entry, 'link', '')

                # 比對紀錄
                if account in PROCESSED_DATA and PROCESSED_DATA[account] == post_id:
                    break
                
                # 排除轉推 (Nitter 風格)
                if title.startswith("RT by") or title.startswith("RT @"):
                    continue
                
                x_link = convert_to_x_link(link)
                new_posts.append((post_id, x_link))

            if new_posts:
                print(f"[*] @{account} 發現 {len(new_posts)} 則新推文")
                for p_id, p_link in reversed(new_posts):
                    message = f"<b>來自 @{account} 的新推文</b>\n\n{p_link}"
                    if await send_telegram(session, config, message):
                        PROCESSED_DATA[account] = p_id
                        save_db()
                        await asyncio.sleep(1) # 避開速率限制
            return # 成功獲取則跳出實例輪詢
        
    print(f"[-] @{account} 所有實例目前皆無法存取")

async def main_loop():
    global DEBUG_MODE
    print(f"----------------------------------------")
    print(f"Social Forwarder 啟動中...")
    print(f"當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"----------------------------------------")

    load_db()
    
    if not BOT_TOKEN:
        print("[X] 錯誤：.env 缺少 TG_BOT_TOKEN")
        return

    async with aiohttp.ClientSession() as session:
        while True:
            config = load_all_configs()
            DEBUG_MODE = config.get("debug", False)
            accounts = config.get("accounts", [])
            instances = config.get("nitter_instances", [])
            interval = config.get("check_interval", 600)

            print(f"[*] 開始輪詢 {len(accounts)} 個帳號...")
            
            for account in accounts:
                await check_account(session, account, instances, config)
                await asyncio.sleep(2) # 帳號間間隔

            print(f"[*] 輪詢結束，等候 {interval} 秒...")
            await asyncio.sleep(interval)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n[!] 程式已手動停止")
    except Exception as e:
        print(f"\n[X] 發生嚴重錯誤: {e}")

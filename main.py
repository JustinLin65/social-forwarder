# Social Forwarder v1.2.0
import os
import asyncio
import json
import aiohttp
import feedparser
import time
import html
import re
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==================== 配置與路徑 ====================
CONFIG_FILE = "config.json"
DB_FILE = "processed_posts.json"

# 全域變數
PROCESSED_DATA = {}
DEBUG_MODE = False

# ==================== 核心邏輯 ====================

def smart_split(text, limit):
    """將文字依照限制長度拆分，優先尋找句號、逗號或換行符號"""
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]
    
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
            
        split_at = -1
        # 尋找分割點，優先順序：換行 > 中文句號 > 英文句號 > 中文逗號 > 英文逗號 > 空格
        for d in ["\n", "。", ".", "，", ",", " "]:
            pos = text.rfind(d, 0, limit)
            if pos > split_at:
                split_at = pos
        
        if split_at == -1:
            split_at = limit
        else:
            split_at += 1 # 包含分隔符
            
        chunk = text[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        text = text[split_at:].lstrip()
        
    return chunks if chunks else [""]

async def process_with_ai(session, text, ai_config):
    """將文字透過 AI (Gemini) 進行處理，包含指數退避重試與動態超時機制"""
    # 預先定義失敗時的回傳內容
    fail_response = f"(API調用失敗，直接發送原文)\n\n{text}"

    if not GEMINI_API_KEY:
        print("   [!] 錯誤：缺少 GEMINI_API_KEY，無法進行 AI 處理")
        return fail_response
    
    model = ai_config.get("model", "gemini-2.5-flash")
    prompt = ai_config.get("prompt", "")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{prompt}\n\n{text}"}]
        }]
    }
    
    max_retries = 3
    base_timeout = 30 # 基礎超時秒數
    
    for attempt in range(max_retries):
        # 動態增加超時時間：30s -> 60s -> 90s
        current_timeout = base_timeout * (attempt + 1)
        
        try:
            async with session.post(url, json=payload, timeout=current_timeout) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            return parts[0].get("text", text).strip()
                    
                    print("   [!] API 回應結構異常，直接發送原文")
                    return fail_response
                
                # 處理 429 (速率限制) 或 503 (服務忙碌) 或 500 (內部錯誤)
                elif resp.status in [429, 500, 503]:
                    # 指數退避：5s -> 10s -> 20s
                    wait_time = 5 * (2 ** attempt)
                    print(f"   [!] Gemini API 忙碌或錯誤 (HTTP {resp.status})，將在 {wait_time} 秒後重試 (超時增加至 {current_timeout + base_timeout}s)...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    error_msg = await resp.text()
                    print(f"   [!] Gemini API 請求失敗 (HTTP {resp.status}): {error_msg}")
                    return fail_response
                    
        except asyncio.TimeoutError:
            wait_time = 5 * (2 ** attempt)
            print(f"   [!] 請求超時 ({current_timeout}s)，將在 {wait_time} 秒後進行下一次嘗試...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 5 * (2 ** attempt)
                print(f"   [!] AI 處理異常: {e}，正在重試...")
                await asyncio.sleep(wait_time)
            else:
                print(f"   [!] AI 處理在 {max_retries} 次嘗試後仍失敗: {e}")
                return fail_response
    
    return fail_response

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

async def send_telegram(session, config, text, media_items=None):
    """發送訊息至 Telegram"""
    tg_conf = config.get("telegram", {})
    bot_token = BOT_TOKEN
    chat_id = tg_conf.get("chat_id")
    topic_id = tg_conf.get("topic_id")
    disable_preview = not tg_conf.get("show_preview", True)
    
    base_payload = {"chat_id": chat_id}
    if topic_id:
        base_payload["message_thread_id"] = topic_id

    async def send_text_msg(msg_text):
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            **base_payload,
            "text": msg_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview
        }
        async with session.post(url, json=payload, timeout=15) as resp:
            return resp.status == 200

    try:
        if media_items and len(media_items) > 0:
            chunks = smart_split(text, 1024)
            first_caption = chunks[0] if chunks else ""
            success = False
            
            if len(media_items) == 1:
                item = media_items[0]
                m_type = item.get("type", "photo")
                m_url = item.get("url")
                method = "sendPhoto" if m_type == "photo" else "sendVideo"
                payload = {**base_payload, m_type: m_url, "caption": first_caption, "parse_mode": "HTML"}
                url = f"https://api.telegram.org/bot{bot_token}/{method}"
                async with session.post(url, json=payload, timeout=30) as resp:
                    success = (resp.status == 200)
            else:
                url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"
                media = []
                for i, item in enumerate(media_items):
                    m_type = item.get("type", "photo")
                    m_url = item.get("url")
                    media_obj = {"type": m_type, "media": m_url}
                    if i == 0:
                        media_obj["caption"] = first_caption
                        media_obj["parse_mode"] = "HTML"
                    media.append(media_obj)
                payload = {**base_payload, "media": media}
                async with session.post(url, json=payload, timeout=40) as resp:
                    success = (resp.status == 200)
            
            if success and len(chunks) > 1:
                for chunk in chunks[1:]:
                    await asyncio.sleep(0.5)
                    await send_text_msg(chunk)
            return success
        else:
            chunks = smart_split(text, 4096)
            overall_success = True
            for i, chunk in enumerate(chunks):
                if not chunk: continue
                if i > 0: await asyncio.sleep(0.5)
                res = await send_text_msg(chunk)
                if i == 0: overall_success = res
            return overall_success
    except Exception as e:
        print(f"   [!] Telegram 發送異常: {e}")
        return False

async def fetch_rss(session, url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        async with session.get(url, headers=headers, timeout=20) as resp:
            if resp.status == 200:
                content = await resp.text()
                return feedparser.parse(content)
            return None
    except Exception:
        return None

async def check_account(session, account, instances, config):
    global PROCESSED_DATA
    tg_conf = config.get("telegram", {})
    ai_conf = config.get("ai", {})
    show_link = tg_conf.get("show_link", True)
    show_text = tg_conf.get("show_text", True)
    ai_enabled = ai_conf.get("enabled", False)

    for instance in instances:
        rss_url = f"{instance.rstrip('/')}/{account}/rss"
        feed = await fetch_rss(session, rss_url)
        if feed and feed.entries:
            new_posts = []
            for entry in feed.entries[:10]:
                post_id = entry.id
                title = getattr(entry, 'title', '')
                link = getattr(entry, 'link', '')
                if account in PROCESSED_DATA and PROCESSED_DATA[account] == post_id:
                    break
                if title.startswith("RT by") or title.startswith("RT @"):
                    continue
                x_link = convert_to_x_link(link)
                media_items = []
                description = getattr(entry, 'description', '')
                if description:
                    video_matches = re.findall(r'<source [^>]*src="([^"]+)"', description)
                    for v_url in video_matches:
                        if '/video/' in v_url or v_url.endswith('.mp4'):
                            media_items.append({"type": "video", "url": f"{instance.rstrip('/')}{v_url}" if v_url.startswith('/') else v_url})
                    img_matches = re.findall(r'<img [^>]*src="([^"]+)"', description)
                    for img_url in img_matches:
                        if '/pic/' in img_url and '/profile_images/' not in img_url:
                            media_items.append({"type": "photo", "url": f"{instance.rstrip('/')}{img_url}" if img_url.startswith('/') else img_url})

                processed_text = title
                if ai_enabled and title:
                    print(f"   [*] 正在對 @{account} 的貼文進行 AI 處理...")
                    processed_text = await process_with_ai(session, title, ai_conf)
                new_posts.append((post_id, x_link, processed_text, media_items))

            if new_posts:
                print(f"[*] @{account} 發現 {len(new_posts)} 則新推文")
                for p_id, p_link, p_text, p_media in reversed(new_posts):
                    success = False
                    if show_link:
                        await send_telegram(session, config, p_link)
                        await asyncio.sleep(0.5)
                    if show_text:
                        full_msg_text = f"<b>來自 @{account} 的新推文</b>\n\n{html.escape(p_text)}"
                        if await send_telegram(session, config, full_msg_text): success = True
                        await asyncio.sleep(0.5)
                    if show_text and p_media:
                        if await send_telegram(session, config, "", p_media): success = True
                    if success:
                        PROCESSED_DATA[account] = p_id
                        save_db()
                        await asyncio.sleep(1)
            return
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
                await asyncio.sleep(2)
            print(f"[*] 輪詢結束，等候 {interval} 秒...")
            await asyncio.sleep(interval)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n[!] 程式已手動停止")
    except Exception as e:
        print(f"\n[X] 發生嚴重錯誤: {e}")
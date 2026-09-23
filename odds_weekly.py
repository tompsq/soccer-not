import os, time, requests, re
from datetime import datetime
from playwright.sync_api import sync_playwright

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(txt):
    if not T or not C: return
    try:
        requests.post(f"https://api.telegram.org/bot{T}/sendMessage", json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"}, timeout=30)
        time.sleep(1)
    except Exception as e: print(e)

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    blocks = []
    
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        pg = b.new_context(viewport={"width": 1440, "height": 900}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)").new_page()
        try:
            # 直接进入英超页面，比从首页点击寻找更稳定
            pg.goto("https://www.pinnacle.com/en/soccer/england/premier-league/matchups", timeout=45000, wait_until="domcontentloaded")
            time.sleep(5)
            
            # 滚动加载
            for _ in range(4):
                pg.evaluate("() => { document.querySelectorAll('div').forEach(el => { if (el.scrollHeight > el.clientHeight) el.scrollTop += 600; }); window.scrollBy(0, 800); }")
                time.sleep(1.5)
            time.sleep(2)
            
            # 获取文本并提取
            lines = [l.strip() for l in pg.evaluate("() => document.body.innerText").split('\n') if l.strip()]
            start = False
            for l in lines:
                if "England - Premier League" in l: 
                    start = True
                    continue 
                if start:
                    if "About Pinnacle" in l or "Responsible Gaming" in l or "Choose Pinnacle" in l: break
                    # 清洗：1.过滤 +10 这种提示  2.只保留纯数字小数（如 1.625）或 "vs" 行
                    if re.match(r'^\+\d+$', l): continue
                    if not re.search(r'\d+\.\d+', l) and " vs " not in l: continue
                    blocks.append(l)
        except Exception as e: 
            print(f"抓取异常: {e}")
        finally: 
            b.close()
            
    if blocks:
        parsed, i = [], 0
        while i < len(blocks):
            # 用 " vs " 精准定位对阵行
            if " vs " in blocks[i] and len(blocks[i]) < 60 and not re.search(r'\d+\.\d+', blocks[i]):
                title = blocks[i]
                i += 1
                m_time, odds = "未定时", []
                while i < len(blocks):
                    nxt = blocks[i]
                    if " vs " in nxt and len(nxt) < 60 and not re.search(r'\d+\.\d+', nxt): break
                    # 只匹配 15:30 这种时间格式
                    if re.match(r'^\d{2}:\d{2}$', nxt): m_time = nxt
                    else: odds.append(nxt)
                    i += 1
                
                ml = [f"⚽ *{title}* 🕒 `{m_time}`"]
                if odds:
                    to = [o for o in odds if re.search(r'\d+\.\d+', o)] # 确保是赔率数字
                    if len(to) >= 3: ml.append(f"   🔹 `1X2` : " + " | ".join(to[:3]))
                    if len(to) >= 7: ml.append(f"   🔹 `亚盘` : " + " | ".join(to[3:7]))
                    if len(to) >= 9: ml.append(f"   🔹 `大小` : " + " | ".join(to[7:]))
                    elif len(to) > 3: ml.append(f"   🔹 `盘口`: " + " | ".join(to[3:]))
                
                if len(ml) > 1: parsed.append("\n".join(ml))
            else: i += 1
            
        if parsed:
            mid = max(1, len(parsed) // 2)
            send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
            send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
        else: send(f"⚠️ `{ts}` 未解析到有效的赛事与赔率。")
    else: send(f"⚠️ `{ts}` 未抓取到网页文字。")

if __name__ == "__main__": main()

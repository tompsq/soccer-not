import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TG_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_tg(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={
            "chat_id": TG_CHAT_ID, "text": text[:4000], "parse_mode": "Markdown"
        }, timeout=30)
    except Exception as e:
        print(f"发送异常: {e}")

def format_match_data(raw_lines):
    """将一列乱序的文本重新格式化为清晰的对阵盘口排版"""
    formatted = ["🎯 *【Pinnacle 英超精排盘口】*"]
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        
        # 识别日期行
        if ", 202" in line or "SAT" in line or "SUN" in line or "MON" in line:
            formatted.append(f"\n📅 *{line}*")
            i += 1
            continue
            
        # 识别比赛对阵（带有 (Match) 标记）
        if i + 1 < len(raw_lines) and "(Match)" in raw_lines[i] and "(Match)" in raw_lines[i+1]:
            home = raw_lines[i].replace(" (Match)", "")
            away = raw_lines[i+1].replace(" (Match)", "")
            i += 2
            
            # 尝试往后抓取时间和赔率
            match_time = "未定时"
            odds = []
            
            # 向后扫描约 15 行收集该场比赛的数据
            scan_count = 0
            while i < len(raw_lines) and scan_count < 15:
                nxt = raw_lines[i]
                # 如果遇到下一场比赛或者新日期，停止当前场次收集
                if "(Match)" in nxt or ", 202" in nxt:
                    break
                if ":" in nxt and len(nxt) <= 5:  # 类似 15:30 的时间
                    match_time = nxt
                else:
                    odds.append(nxt)
                i += 1
                scan_count += 1
                
            # 组装这场比赛的排版
            match_str = f"\n⚽ *{home} vs {away}* 🕒 `{match_time}`"
            if odds:
                # 简单分类展示赔率（可根据需要微调）
                match_str += f"\n   🔹 1X2/盘口数据: " + " | ".join(odds[:6])
            formatted.append(match_str)
        else:
            i += 1
            
    return "\n".join(formatted)

def main():
    t_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines_out = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        page = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36").new_page()
        
        try:
            page.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 1. 点击 LEAGUES
            page.evaluate("() => { const t = Array.from(document.querySelectorAll('button, div, span, a')).find(el => el.textContent.trim().toUpperCase() === 'LEAGUES'); if (t) t.click(); }")
            time.sleep(4)
            
            # 2. 点击英超
            success = page.evaluate("() => { const l = Array.from(document.querySelectorAll('a')); let t = l.find(el => el.textContent.includes('Premier League')); if (!t) t = Array.from(document.querySelectorAll('div, span, li')).find(el => el.textContent.trim() === 'England - Premier League'); if (t) { t.scrollIntoView(); t.dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true, buttons: 1})); return true; } return false; }")
            if not success:
                page.locator("text=England - Premier League").first.click(force=True)
                
            time.sleep(8)
            
            # 3. 滚动加载所有赛事
            for _ in range(4):
                page.evaluate("""() => {
                    const scrollers = document.querySelectorAll('div');
                    scrollers.forEach(el => { if (el.scrollHeight > el.clientHeight) { el.scrollTop += 600; } });
                    window.scrollBy(0, 800);
                }""")
                time.sleep(1.5)
            time.sleep(3)
            
            # 4. 提取纯文本
            body_text = page.evaluate("() => document.body.innerText")
            raw_lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            
            start = False
            for l in raw_lines:
                if "England - Premier League" in l or "1X2" in l:
                    start = True
                if start:
                    if "About Pinnacle" in l or "Responsible Gaming" in l: break
                    lines_out.append(l)
        except Exception as e:
            print(f"异常: {e}")
        finally:
            browser.close()
            
    if lines_out:
        # 使用排版函数进行美化
        formatted_msg = format_match_data(lines_out)
        final_output = f"{formatted_msg}\n\n🕒 更新时间: `{t_str}`"
        send_tg(final_output)
    else:
        send_tg(f"⚠️ *【监控提醒】* `{t_str}` 未能抓取到文字。")

if __name__ == "__main__":
    main()

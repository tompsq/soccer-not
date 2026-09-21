import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

def fetch_odds_and_screenshot():
    print("🌐 启动浏览器开始执行点击流程...")
    screenshot_path = "pinnacle_epl.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900}, 
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            # 1. 访问首页
            page.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            print("⏳ 等待首页加载...")
            time.sleep(6)
            
            # 2. 点击 LEAGUES 标签
            print("📋 正在寻找并点击 LEAGUES...")
            page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const t = tabs.find(el => el.textContent && el.textContent.trim().toUpperCase() === 'LEAGUES');
                if(t) t.click();
            }""")
            time.sleep(4)
            
            # 3. 点击英超 (England - Premier League)
            print("🎯 正在寻找并点击英超...")
            clicked = page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('div, span, a'));
                const epl = els.find(el => el.textContent && el.textContent.includes('England - Premier League'));
                if(epl) {
                    let btn = epl.closest('a') || epl.closest('div[role="button"]') || epl;
                    btn.click();
                    return true;
                }
                return false;
            }""")
            print(f"🔍 英超点击动作执行状态: {clicked}")
            
            # 给足时间让英超盘口页面完全渲染
            print("⏳ 等待英超盘口页面渲染...")
            time.sleep(10)
            
            # 4. 关键：把当前页面截下来保存
            print(f"📸 正在保存当前页面截图到 {screenshot_path}...")
            page.screenshot(path=screenshot_path, full_page=True)
            
            # 5. 提取文字
            body_text = page.evaluate("() => document.body.innerText")
            browser.close()
            
            # 6. 清洗文本（过滤掉顶部杂项导航，只保留核心盘口）
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            
            clean_lines = []
            start_collect = False
            for l in lines:
                # 寻找盘口开始的标志
                if "England - Premier League" in l or "1X2" in l or "Spread" in l:
                    start_collect = True
                
                if start_collect:
                    if "About Pinnacle" in l or "Responsible Gaming" in l:
                        break
                    clean_lines.append(l)
            
            if len(clean_lines) > 5:
                print(f"✅ 成功清洗出 {len(clean_lines)} 行盘口数据")
                return screenshot_path, clean_lines[:35]
            else:
                print("⚠️ 未能精准匹配，采用黑名单过滤...")
                blacklist = ["LOG IN", "JOIN", "SPORTS BETTING", "LIVE CENTRE", "CASINO", "Cookie", "ACCEPT", "Privacy"]
                filtered = [l for l in lines if not any(b in l for b in blacklist)]
                return screenshot_path, filtered[:35]
                
        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            if os.path.exists(screenshot_path):
                try: browser.close()
                except: pass
            return None, None

def send_to_telegram(screenshot_path, lines):
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("❌ 缺少 Telegram 环境变量")
        return
    
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 先发送截图，让老哥一眼看出点到哪里了
    if screenshot_path and os.path.exists(screenshot_path):
        print("📤 正在向 Telegram 发送网页截图...")
        with open(screenshot_path, "rb") as photo:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": f"📸 *【网页实时截图】* - `{t}`", "parse_mode": "Markdown"},
                files={"photo": photo},
                timeout=30
            )
    
    # 2. 再发送抓取到的精简文字盘口
    if lines:
        print("📤 正在向 Telegram 发送提取的盘口文字...")
        msg = f"🎯 *【Pinnacle 英超盘口文字】*\n🕒 `{t}`\n\n```text\n" + "\n".join(lines) + "\n```"
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=30
        )
    print("✅ 全部推送流程完成")

if __name__ == "__main__":
    img_path, data = fetch_odds_and_screenshot()
    if img_path or data:
        send_to_telegram(img_path, data)
    else:
        print("❌ 未能获取到任何数据或截图")

import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

def fetch_odds():
    print("🌐 启动浏览器抓取 Pinnacle 英超盘口...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")
        page = context.new_page()
        try:
            page.goto("https://www.pinnacle.com/en/soccer/matchups", timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
            
            # 点击 LEAGUES
            print("📋 正在寻找并点击 LEAGUES...")
            page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('button, div, span, a'));
                const t = tabs.find(el => el.textContent && el.textContent.trim().toUpperCase() === 'LEAGUES');
                if(t) t.click();
            }""")
            time.sleep(4)
            
            # 点击英超
            print("🎯 正在寻找并点击英超...")
            page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('div, span, a'));
                const epl = els.find(el => el.textContent && el.textContent.includes('England - Premier League'));
                if(epl) {
                    let btn = epl.closest('a') || epl.closest('div[role="button"]') || epl;
                    btn.click();
                }
            }""")
            
            # 增加更长的等待时间，确保盘口赔率表格完全加载
            print("⏳ 等待盘口赔率表格渲染...")
            time.sleep(10)
            
            # 提取文本
            body_text = page.evaluate("() => document.body.innerText")
            browser.close()
            
            # 清洗文本：过滤掉导航栏、Cookie、登录等杂项，只留赛程和赔率
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            
            clean_lines = []
            start_collect = False
            
            for l in lines:
                # 寻找英超盘口核心区域的标志性文字
                if "England - Premier League Odds" in l or "SAT, OCT" in l or "SUN, OCT" in l:
                    start_collect = True
                
                if start_collect:
                    # 碰到底部版权信息就停止收集
                    if "About Pinnacle" in l or "Responsible Gaming" in l:
                        break
                    clean_lines.append(l)
            
            # 如果成功精准截取到赛程区域
            if len(clean_lines) > 10:
                print(f"✅ 成功提取到 {len(clean_lines)} 行核心盘口数据")
                return clean_lines[:40]
            else:
                print("⚠️ 未能精准过滤，采用智能后段切片...")
                # 过滤掉常见的导航关键词
                filtered = [l for l in lines if not any(kw in l for kw in ["LOG IN", "JOIN", "SPORTS BETTING", "LIVE CENTRE", "CASINO", "Cookie", "ACCEPT"])]
                return filtered[:35]
                
        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            browser.close()
            return None

def send_tg(lines):
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return
    
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"🎯 *【Pinnacle 英超盘口】*\n🕒 `{t}`\n\n```text\n" + "\n".join(lines) + "\n```"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
        "chat_id": chat_id, "text": msg, "parse_mode": "Markdown"
    })
    print("✅ 精简盘口数据推送完成")

if __name__ == "__main__":
    data = fetch_odds()
    if data: 
        send_tg(data)
    else:
        print("❌ 没有获取到有效数据")

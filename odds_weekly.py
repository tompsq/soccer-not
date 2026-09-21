import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

def fetch_odds():
    print("🌐 直接启动浏览器访问 Pinnacle 英超盘口直达页面...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900}, 
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            # 直接访问英超赛事直达链接
            target_url = "https://www.pinnacle.com/en/soccer/english-premier-league/matchups"
            print(f"🔗 正在打开: {target_url}")
            page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            
            # 给予充足时间让赔率异步表格渲染出来
            print("⏳ 等待英超盘口赔率数据异步加载...")
            time.sleep(10)
            
            # 提取页面全文本
            body_text = page.evaluate("() => document.body.innerText")
            browser.close()
            
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            print(f"📊 成功抓取到原始内容，总行数: {len(lines)}")
            
            # 过滤掉顶部网站导航、Cookie 声明等垃圾信息，只保留赛事和赔率
            clean_lines = []
            start_collect = False
            
            for l in lines:
                # 当看到带有赔率特征或者比赛日期时开始收集
                if "Premier League" in l or "1X2" in l or "Spread" in l or "Total" in l:
                    start_collect = True
                
                if start_collect:
                    if "About Pinnacle" in l or "Responsible Gaming" in l or "Privacy Policy" in l:
                        break
                    clean_lines.append(l)
            
            # 如果成功截取到核心段落
            if len(clean_lines) > 10:
                print(f"✅ 成功清洗出 {len(clean_lines)} 行盘口数据")
                return clean_lines[:40]
            else:
                print("⚠️ 未能精准匹配，采用黑名单过滤掉通用导航...")
                blacklist = ["LOG IN", "JOIN", "SPORTS BETTING", "LIVE CENTRE", "CASINO", "Cookie", "ACCEPT", "Privacy", "Help"]
                filtered = [l for l in lines if not any(b in l for b in blacklist)]
                return filtered[:40]
                
        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            browser.close()
            return None

def send_tg(lines):
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("❌ 缺少 Telegram 环境变量")
        return
    
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"🎯 *【Pinnacle 英超盘口直达】*\n🕒 `{t}`\n\n```text\n" + "\n".join(lines) + "\n```"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={
        "chat_id": chat_id, 
        "text": msg, 
        "parse_mode": "Markdown"
    }, timeout=30)
    
    if res.status_code == 200:
        print("✅ 盘口数据成功推送至 Telegram")
    else:
        print(f"⚠️ 推送失败: {res.text}")

if __name__ == "__main__":
    data = fetch_odds()
    if data: 
        send_tg(data)
    else:
        print("❌ 没有获取到有效数据")

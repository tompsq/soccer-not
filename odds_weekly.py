import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# === 第一部分：获取与清洗盘口 ===
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
            time.sleep(8)
            
            # 提取文本
            body_text = page.evaluate("() => document.body.innerText")
            browser.close()
            
            # 清洗文本
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            print(f"📊 网页总共提取到 {len(lines)} 行文本")
            
            start, clean_lines = False, []
            for l in lines:
                if "England - Premier League Odds" in l: 
                    start = True
                if start:
                    if "About Pinnacle" in l: 
                        break
                    clean_lines.append(l)
            
            if clean_lines:
                print(f"✅ 成功精准截取到 {len(clean_lines)} 行盘口数据")
                return clean_lines[:35]
            else:
                print("⚠️ 未能精准匹配到英超关键词，改用兜底策略（前 30 行）")
                return lines[:30]
                
        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            browser.close()
            return None

# === 第二部分：推送至 Telegram ===
def send_tg(lines):
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    # 打印环境变量检查状态（不会泄露完整密钥，只看有没有值）
    print(f"🔍 检查环境变量 -> TG_BOT_TOKEN: {'已配置' if token else '未配置！'}, TG_CHAT_ID: {'已配置' if chat_id else '未配置！'}")
    
    if not token or not chat_id:
        print("❌ 错误：缺少 Telegram 环境变量，无法发送！请检查 GitHub Secrets 配置。")
        return
    
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"🎯 *【Pinnacle 英超盘口】*\n🕒 `{t}`\n\n```text\n" + "\n".join(lines) + "\n```"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": msg, 
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=30)
        print(f"📨 Telegram API 响应状态码: {res.status_code}")
        print(f"📨 Telegram API 响应内容: {res.text}")
        if res.status_code == 200:
            print("✅ Telegram 消息推送成功！")
        else:
            print("⚠️ Telegram 消息推送失败，请检查 Chat ID 或 Token 是否正确。")
    except Exception as e:
        print(f"❌ 发送请求异常: {e}")

if __name__ == "__main__":
    data = fetch_odds()
    if data: 
        send_tg(data)
    else:
        print("❌ 没有获取到任何有效数据，跳过推送。")
        # 即使没抓到也发个提示到 TG 方便排查
        token = os.environ.get("TG_BOT_TOKEN")
        chat_id = os.environ.get("TG_CHAT_ID")
        if token and chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id, 
                "text": "⚠️ 监控脚本运行完成，但未抓取到有效盘口数据。"
            })

import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TG_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_photo(photo_path, caption):
    """通过 Telegram Bot 发送截图"""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            payload = {
                "chat_id": TG_CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            files = {"photo": photo}
            res = requests.post(url, data=payload, files=files, timeout=30)
            if res.status_code == 200:
                print("✅ Pinnacle 盘口截图推送成功")
            else:
                print(f"❌ 推送失败: {res.text}")
    except Exception as e:
        print(f"❌ 发送异常: {str(e)}")

def capture_pinnacle_odds():
    """使用无头浏览器突破反爬并截取 Pinnacle 赛事页面"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    screenshot_path = "pinnacle_odds.png"
    
    with sync_playwright() as p:
        # 启动浏览器，设置较为真实的桌面/移动端窗口
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled", # 核心：隐藏自动化特征
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        page = context.new_page()
        
        try:
                        # 修正后的 Pinnacle 足球大厅公开入口
            target_url = "https://www.pinnacle.com/en/soccer/matchups"
            print(f"🌐 正在连接 Pinnacle: {target_url}")
            
            # 以 domcontentloaded 导航，避免被过长的子资源加载拖死
            page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            
            # 留出充足时间让 Cloudflare 验证通过、动态盘口和赔率数字渲染出来
            print("⏳ 等待动态赔率数据渲染...")
            time.sleep(8)
            
            # 截取全屏或当前视口
            page.screenshot(path=screenshot_path, full_page=True)
            print("📸 Pinnacle 页面截图成功")
            
        except Exception as e:
            print(f"⚠️ 访问 Pinnacle 异常: {str(e)}")
            # 即使报错也尝试截一张当前的报错/拦截画面，方便排查
            try:
                page.screenshot(path=screenshot_path)
            except:
                pass
        finally:
            browser.close()
            
    # 推送至 Telegram
    caption = f"🎯 *【Pinnacle 平博盘口视觉监控】*\n🕒 抓取时间: `{current_time}`\n🚀 状态: 无头浏览器实时截图"
    if os.path.exists(screenshot_path):
        send_telegram_photo(screenshot_path, caption)

def main():
    print("🔄 正在启动 Pinnacle 监控任务...")
    capture_pinnacle_odds()

if __name__ == "__main__":
    main()

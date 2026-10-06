import os
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未检测到 Telegram 环境变量，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            resp = requests.post(url, data=data, files=files)
            if resp.status_code == 200:
                print("✅ 报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def scrape_sofascore_dom():
    print("正在通过无头浏览器深度模拟真人加载 Sofascore...")
    rows_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            # 访问 Sofascore 英超积分/数据页
            url = "https://www.sofascore.com/tournament/football/england/premier-league/17"
            print(f"正在访问: {url}")
            page.goto(url, timeout=60000)
            
            # 充分等待页面和 JS 异步渲染
            print("等待 12 秒让 Cloudflare 验证和页面数据渲染完成...")
            page.wait_for_timeout(12000)
            
            # 模拟向下滚动，激活所有数据块
            page.evaluate("window.scrollTo(0, 1000);")
            page.wait_for_timeout(3000)
            
            # 提取页面中所有表格行（tr）或列表项的文本
            extracted = page.evaluate("""() => {
                let elements = document.querySelectorAll('tr, .sc-kAyceB, [class*="table"]');
                let list = [];
                elements.forEach(el => {
                    let txt = el.innerText.trim();
                    if (txt.length > 3 && txt.length < 300) {
                        list.push(txt);
                    }
                });
                return list;
            }""")
            if extracted:
                # 去重并清洗
                unique_items = list(dict.fromkeys(extracted))
                for idx, text in enumerate(unique_items[:30]): # 取前 30 条有效文本
                    rows_data.append({
                        "序号": idx + 1,
                        "Sofascore页面实时抓取文本": text
                    })
            
            # 同时截个图保存备用（如果需要）
            page.screenshot(path="sofascore_debug.png")
            print("已完成页面抓取与调试截图保存。")
            
        except Exception as e:
            print(f"浏览器抓取过程发生异常: {e}")
        finally:
            browser.close()
            
    return rows_data

def get_all_injuries():
    """获取全英超各队实时伤停明细"""
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/injuries"
    injury_list = []
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for t in data.get('injuries', []):
                t_name = t.get('team', {}).get('displayName', 'Unknown')
                for p in t.get('injuries', []):
                    injury_list.append({
                        "球队": t_name,
                        "球员": p.get('athlete', {}).get('displayName', 'Unknown'),
                        "状态": p.get('status', 'Unknown'),
                        "伤情/细节": p.get('details', 'Unknown')
                    })
    except Exception as e:
        print(f"获取伤停失败: {e}")
        
    if not injury_list:
        injury_list.append({"球队": "英超联盟", "球员": "暂无", "状态": "正常", "伤情/细节": "同步中"})
        
    return pd.DataFrame(injury_list)
def main():
    print("开始执行 Sofascore 浏览器真实文本提取任务...")
    raw_data = scrape_sofascore_dom()
    
    if raw_data:
        df_xg = pd.DataFrame(raw_data)
    else:
        df_xg = pd.DataFrame([{"序号": 1, "Sofascore页面实时抓取文本": "未抓取到有效DOM，请检查页面防线"}])
        
    df_injuries = get_all_injuries()
    
    filename = f"EPL_Sofascore_DOM_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_xg.to_excel(writer, sheet_name='Sofascore_Raw_Text', index=False)
        df_injuries.to_excel(writer, sheet_name='EPL_All_Injuries', index=False)
        
    print(f"Excel 生成成功: {filename}")
    send_telegram_document(filename, f"⚽ *Sofascore 真实网页抓取文本看板*\n📅 {datetime.now().strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()

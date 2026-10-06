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
                print("✅ 真实网页抓取的 xG 报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def scrape_sofascore_xg_with_browser():
    print("正在启动无头浏览器，准备真实模拟访问 Sofascore...")
    extracted_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            # 访问 Sofascore 英超主页面
            url = "https://www.sofascore.com/tournament/football/england/premier-league/17"
            print(f"正在打开页面: {url}")
            page.goto(url, timeout=60000)
            
            # 像真人一样等待页面加载与 Cloudflare 验证通过
            print("等待页面完全渲染...")
            page.wait_for_timeout(10000)
            
            # 滚动页面以触发所有懒加载元素
            page.evaluate("window.scrollTo(0, 800)")
            page.wait_for_timeout(3000)
            
            # 尝试抓取表格或统计容器中的文本
            # 打印当前页面的部分文本用于日志排查
            page_title = page.title()
            print(f"当前页面标题: {page_title}")
            
            # 提取页面中所有包含球队统计的行
            rows_data = page.evaluate("""() => {
                let rows = document.querySelectorAll('div, tr');
                let results = [];
                rows.forEach(r => {
                    let text = r.innerText.trim();
                    // 过滤出可能包含球队名和数值的行
                    if (text.length > 0 && text.length < 200) {
                        results.push(text);
                    }
                });
                return results;
            .slice(0, 50))}""") # 限制返回避免过大
            
            # 如果能定位到具体的积分榜/数据表格结构
            table_rows = page.querySelectorAll('tr')
            print(f"检测到页面中的表格行数: {len(table_rows)}")
            
            parsed_rows = []
            for tr in table_rows:
                row_text = tr.inner_text().strip()
                if row_text:
                    parsed_rows.append({"原始网页文本": row_text})
            
            if parsed_rows:
                extracted_data = parsed_rows[:20] # 取前20支球队
                
        except Exception as e:
            print(f"浏览器抓取出错: {e}")
        finally:
            browser.close()
            
    return extracted_data

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
    print("开始执行无头浏览器 xG 抓取任务...")
    raw_data = scrape_sofascore_xg_with_browser()
    
    if raw_data:
        df_xg = pd.DataFrame(raw_data)
    else:
        df_xg = pd.DataFrame([{"球队": "抓取受阻_等待调整选择器", "状态": "检查Action日志"}])
        
    df_injuries = get_all_injuries()
    
    filename = f"EPL_Browser_Scrape_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_xg.to_excel(writer, sheet_name='EPL_Cumulative_xG', index=False)
        df_injuries.to_excel(writer, sheet_name='EPL_All_Injuries', index=False)
        
    print(f"Excel 生成成功: {filename}")
    send_telegram_document(filename, f"⚽ *Sofascore 浏览器抓取结果* \n📅 {datetime.now().strftime('%Y-%m-%d')}")

if __name__ == "main__":
    main()

import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_xgscore_table():
    url = "https://xgscore.io/xg-statistics/epl"
    print(f"正在访问具体联赛 xG 页面: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="networkidle")
            print(f"页面加载成功，标题为: {page.title()}")
            
            page.wait_for_timeout(6000)
            
            data = []
            rows = page.query_selector_all("table tr")
            if rows:
                for row in rows:
                    cols = row.query_selector_all("th, td")
                    cols_text = [col.inner_text().strip() for col in cols]
                    if cols_text:
                        data.append(cols_text)
            
            if not data:
                print("未检测到标准表格，正在尝试抓取行内容...")
                rows = page.query_selector_all("div.row, tr, li")
                for row in rows:
                    text_content = row.inner_text().strip()
                    if text_content:
                        lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                        if lines and lines not in data:
                            data.append(lines)
            
            if not data:
                print("错误：未能提取到有效数据。")
                return

            # 1. 保存覆盖最新的文件
            latest_file = "xgscore_data.csv"
            with open(latest_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)

            # 2. 存一份带日期时间戳的历史快照（存放在 history 文件夹里）
            os.makedirs("history", exist_ok=True)
            today_str = datetime.now().strftime("%Y%m%d")
            history_file = f"history/xgscore_epl_{today_str}.csv"
            
            with open(history_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"数据抓取成功！已更新 {latest_file} 并保存历史快照至 {history_file}。")
            
        except Exception as e:
            print(f"抓取过程发生错误: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_xgscore_table()

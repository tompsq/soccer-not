import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync  # 导入隐身插件

def scrape_with_stealth():
    url = "https://footystats.org/england/premier-league/xg"
    print(f"正在使用 Stealth 模式访问: {url}")
    
    data = []

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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        # 核心：注入 stealth 脚本，抹除自动化痕迹
        stealth_sync(page)
        
        try:
            # 访问页面，将等待策略调整为 domcontentloaded，避免卡死
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            print("页面打开成功，等待 Cloudflare 自动验证及渲染...")
            
            # 留出 8 秒给 Cloudflare 自动跳转和页面表格渲染
            page.wait_for_timeout(8000)
            
            # 尝试抓取页面表格
            tables = page.query_selector_all("table")
            print(f"检测到 {len(tables)} 个表格。")
            
            target_table = None
            for tbl in tables:
                text = tbl.inner_text()
                if "xG" in text or "Team" in text:
                    target_table = tbl
                    break
            
            if not target_table and tables:
                target_table = tables[0]

            if target_table:
                rows = target_table.query_selector_all("tr")
                for row in rows:
                    cols = row.query_selector_all("th, td")
                    cols_text = [col.inner_text().strip().replace("\n", " ") for col in cols]
                    if cols_text and any(cols_text):
                        data.append(cols_text)
            
            # 如果没抓到标准表格，降级提取所有文本行
            if not data:
                print("未匹配到标准表格，提取正文内容...")
                body_text = page.inner_text("body")
                data = [[line] for line in body_text.split("\n") if line.strip()]

        except Exception as e:
            print(f"抓取异常: {e}")
            data = [["ERROR", str(e)]]
        finally:
            browser.close()

    # 写入文件
    latest_file = "footystats_epl_xg.csv"
    with open(latest_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    os.makedirs("history", exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    history_file = f"history/footystats_epl_{today_str}.csv"
    with open(history_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)
        
    print(f"处理完成，共写入 {len(data)} 行数据。")

if __name__ == "__main__":
    scrape_with_stealth()

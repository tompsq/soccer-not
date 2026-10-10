import csv
import os
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_footystats_xg():
    url = "https://footystats.org/england/premier-league/xg"
    print(f"正在访问 FootyStats xG 页面: {url}")
    
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
        
        try:
            # 访问页面，将超时放宽到 90 秒
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            print(f"页面打开成功，标题: {page.title()}")
            
            # 等待 8 秒让页面加载
            page.wait_for_timeout(8000)
            
            # 尝试提取页面中的表格
            tables = page.query_selector_all("table")
            print(f"检测到页面中包含 {len(tables)} 个表格。")
            
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
            
            # 如果没找到表格，抓取所有段落文本
            if not data:
                print("未匹配到标准表格，抓取页面正文...")
                body_text = page.inner_text("body")
                data = [[line] for line in body_text.split("\n") if line.strip()]

        except Exception as e:
            # 如果中途报错，把错误堆栈写进 data 里，方便我们在 CSV 里直接看到报错原因！
            error_msg = traceback.format_exc()
            print(f"抓取过程发生异常:\n{error_msg}")
            data = [["ERROR_OCCURRED"], [str(e)], [error_msg]]
        finally:
            browser.close()

    # 确保无论成功或失败，都会把内容写入文件，再也不会出现空文件
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
        
    print(f"处理完成，已写入文件，总行数: {len(data)}")

if __name__ == "__main__":
    scrape_footystats_xg()

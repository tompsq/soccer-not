import csv
from playwright.sync_api import sync_playwright

def scrape_xgscore():
    url = "https://xgscore.io/"
    print(f"正在访问目标网页: {url}")
    
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
            # 访问网页
            page.goto(url, timeout=60000, wait_until="networkidle")
            print(f"页面加载成功，标题为: {page.title()}")
            
            # 等待页面中的表格加载出来（xGscore 通常使用 table 结构展示积分榜和 xG 数据）
            try:
                page.wait_for_selector("table", timeout=10000)
            except:
                print("未直接检测到标准 table 标签，尝试等待通用容器...")
            
            # 提取页面中所有表格的行数据
            data = []
            tables = page.query_selector_all("table")
            
            if tables:
                for table in tables:
                    rows = table.query_selector_all("tr")
                    for row in rows:
                        cols = row.query_selector_all("th, td")
                        cols_text = [col.inner_text().strip() for col in cols]
                        if cols_text:
                            data.append(cols_text)
            else:
                # 备用方案：如果没有 table，抓取所有带有文本的行
                rows = page.query_selector_all("tr, div.row, div.table-row")
                for row in rows:
                    cols_text = [c.strip() for c in row.inner_text().split("\n") if c.strip()]
                    if cols_text:
                        data.append(cols_text)
            
            if not data:
                print("警告：仍未抓取到有效数据。")
                return

            output_file = "xgscore_data.csv"
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"数据抓取成功，已保存至 {output_file}，共获取到 {len(data)} 行数据。")
            
        except Exception as e:
            print(f"抓取过程发生错误: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_xgscore()

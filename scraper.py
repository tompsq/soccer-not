import csv
from playwright.sync_api import sync_playwright

def scrape_xgscore():
    # 直接访问具体的联赛 xG 数据页面（以英超为例，你可以更换成其他联赛的链接）
    url = "https://xgscore.io/england/premier-league/xg"
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
            # 访问具体联赛页面
            page.goto(url, timeout=60000, wait_until="networkidle")
            print(f"页面加载成功，标题为: {page.title()}")
            
            # 等待表格加载
            page.wait_for_timeout(5000)
            
            data = []
            
            # 抓取页面中的表格数据
            tables = page.query_selector_all("table")
            if tables:
                for table in tables:
                    rows = table.query_selector_all("tr")
                    for row in rows:
                        cols = row.query_selector_all("th, td")
                        cols_text = [col.inner_text().strip() for col in cols if col.inner_text().strip()]
                        if cols_text:
                            data.append(cols_text)
            
            # 备用方案：如果表格没找到，抓取所有行内容
            if not data:
                print("未检测到标准表格，正在尝试抓取文本行...")
                rows = page.query_selector_all("tr, div.row, li")
                for row in rows:
                    text_content = row.inner_text().strip()
                    if text_content:
                        lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                        if lines and lines not in data:
                            data.append(lines)
            
            if not data:
                print("警告：未能提取到有效数据。")
                return

            output_file = "xgscore_data.csv"
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"数据抓取成功！已保存至 {output_file}，共获取到 {len(data)} 行数据。")
            
        except Exception as e:
            print(f"抓取过程发生错误: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_xgscore()

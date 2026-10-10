import csv
from playwright.sync_api import sync_playwright

def scrape_xgscore_table():
    # 使用正确的英超 xG 统计页面网址
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
            # 访问页面并等待网络空闲
            page.goto(url, timeout=60000, wait_until="networkidle")
            print(f"页面加载成功，标题为: {page.title()}")
            
            # 等待表格或数据加载完成
            page.wait_for_timeout(6000)
            
            data = []
            
            # 尝试抓取页面中的表格行
            rows = page.query_selector_all("table tr")
            if rows:
                for row in rows:
                    cols = row.query_selector_all("th, td")
                    cols_text = [col.inner_text().strip() for col in cols]
                    if cols_text:
                        data.append(cols_text)
            
            # 如果标准表格没抓到，尝试通用的行或列表容器
            if not data:
                print("未检测到标准表格标签，正在尝试抓取行内容...")
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

            # 保存为 CSV 文件
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
    scrape_xgscore_table()

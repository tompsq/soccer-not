import csv
from playwright.sync_api import sync_playwright

def scrape_xgscore_table():
    # 直接访问英超的 xG 统计页面（你可以把链接换成西甲、意甲等其他联赛）
    url = "https://xgscore.io/england/premier-league/xg"
    print(f"正在访问具体联赛页面: {url}")
    
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
            # 访问页面并等待加载完成
            page.goto(url, timeout=60000, wait_until="networkidle")
            print(f"页面加载成功，标题为: {page.title()}")
            
            # 额外等待 5 秒让表格数据完全渲染出来
            page.wait_for_timeout(5000)
            
            data = []
            
            # 精准定位页面中的数据表格（table 标签中的所有行）
            rows = page.query_selector_all("table tr")
            
            if rows:
                for row in rows:
                    # 提取每一行里的表头(th)或单元格(td)文字
                    cols = row.query_selector_all("th, td")
                    cols_text = [col.inner_text().strip() for col in cols]
                    if cols_text:
                        data.append(cols_text)
            
            if not data:
                print("警告：未能在页面中找到标准表格，尝试抓取数据区块...")
                # 备用：抓取所有行或列表项
                elements = page.query_selector_all("div.table-row, tr, li")
                for el in elements:
                    text = el.inner_text().strip()
                    if text:
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if lines and lines not in data:
                            data.append(lines)
            
            if not data:
                print("错误：仍然没有抓到有效数据。")
                return

            # 保存为 CSV 文件
            output_file = "xgscore_data.csv"
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"成功抓取数据！已保存至 {output_file}，共获取到 {len(data)} 行数据。")
            
        except Exception as e:
            print(f"抓取过程发生错误: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_xgscore_table()

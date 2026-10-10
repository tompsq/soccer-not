import csv
import os
from playwright.sync_api import sync_playwright

def scrape_footystats():
    # 目标页面：以英超 xG 数据页面为例（你可以根据需要修改网址）
    url = "https://footystats.org/england/premier-league/xg"
    
    print(f"正在访问目标网页: {url}")
    
    with sync_playwright() as p:
        # 启动浏览器（headless=True 表示无头模式，在 GitHub Actions 中必须开启）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 打开网页并等待加载
            page.goto(url, timeout=60000)
            
            # 等待表格加载（根据网页实际的表格元素调整选择器）
            page.wait_for_selector("table", timeout=30000)
            
            # 提取表格数据
            # 假设网页上有我们需要的统计表格
            data = []
            rows = page.query_selector_all("table tr")
            
            for row in rows:
                cols = row.query_selector_all("th, td")
                cols_text = [col.inner_text().strip() for col in cols]
                if cols_text:
                    data.append(cols_text)
            
            if not data:
                print("警告：未抓取到任何表格数据，可能触发了反爬或选择器需调整。")
                return

            # 将数据保存为 CSV 文件，方便 GitHub Actions 提交
            output_file = "footystats_xg_data.csv"
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"数据抓取成功，已保存至 {output_file}，共抓取到 {len(data)} 行数据。")
            
        except Exception as e:
            print(f"抓取过程发生错误: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_footystats()

import csv
from playwright.sync_api import sync_playwright

def scrape_footystats():
    url = "https://footystats.org/england/premier-league/xg"
    print(f"正在访问目标网页: {url}")
    
    with sync_playwright() as p:
        # 使用非无头模式的参数或添加伪装，防止被识别为机器人
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            # 访问网页，等待网络空闲
            page.goto(url, timeout=60000, wait_until="networkidle")
            
            # 打印当前标题，看看是否成功绕过或被拦截
            print(f"页面标题: {page.title()}")
            
            # 延长等待时间，或者等待页面中更通用的容器加载
            # 如果网站用了 div 布局而不是 table，这里尝试等待任意表格或主要数据区域
            page.wait_for_timeout(5000) # 额外等待 5 秒让 JS 渲染
            
            # 尝试抓取所有行（兼容 table 或通用标签）
            data = []
            rows = page.query_selector_all("table tr, div.row, tr")
            
            for row in rows:
                cols = row.query_selector_all("th, td, div")
                cols_text = [col.inner_text().strip() for col in cols if col.inner_text().strip()]
                if cols_text:
                    data.append(cols_text)
            
            if not data:
                print("警告：未抓取到有效数据，可能被 Cloudflare 拦截。")
                return

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

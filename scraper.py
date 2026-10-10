import csv
from playwright.sync_api import sync_playwright

def scrape_xgscore():
    # 目标网址：以 xGscore 网站的西甲或其他联赛 xG 数据页面为例
    # 如果你有具体的链接，可以把这里替换掉
    url = "https://xgscore.io/"
    
    print(f"正在访问目标网页: {url}")
    
    with sync_playwright() as p:
        # 启动浏览器（采用无头模式，并加入反检测参数，防止被 Cloudflare 或反爬机制拦截）
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        # 模拟真实浏览器的上下文环境（UA、视口大小等）
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            # 访问网页，等待网络空闲
            page.goto(url, timeout=60000, wait_until="networkidle")
            
            print(f"页面加载成功，标题为: {page.title()}")
            
            # 给 JavaScript 额外渲染留出几秒钟时间
            page.wait_for_timeout(5000)
            
            # 尝试抓取表格或页面中的统计行数据
            data = []
            # 兼容表格标签 (table tr) 或者通用的行容器
            rows = page.query_selector_all("table tr, div.row, tr")
            
            for row in rows:
                cols = row.query_selector_all("th, td, div")
                cols_text = [col.inner_text().strip() for col in cols if col.inner_text().strip()]
                if cols_text:
                    data.append(cols_text)
            
            if not data:
                print("警告：未抓取到有效数据，页面可能结构复杂或被拦截。")
                return

            # 保存为 CSV 文件，GitHub Actions 随后会自动将其提交到仓库
            output_file = "xgscore_data.csv"
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"数据抓取成功，已保存至 {output_file}，共获取到 {len(data)} 行数据。")
            
        except Exception as e:
            print(f"抓取过程中发生错误: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_xgscore()

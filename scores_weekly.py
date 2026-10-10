import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_footystats_xg():
    url = "https://footystats.org/england/premier-league/xg"
    print(f"正在访问 FootyStats xG 页面: {url}")
    
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
            # 访问页面
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            print(f"页面打开成功，标题: {page.title()}")
            
            # 留出 6 秒渲染延迟，确保动态内容加载完毕
            page.wait_for_timeout(6000)
            
            # 尝试关闭各种常见的 Cookie 弹窗或广告遮罩
            try:
                cookie_btn = page.query_selector("button#ez-accept-all, .cc-dismiss, button.accept-all, div.fc-button-label")
                if cookie_btn:
                    cookie_btn.click()
                    print("已自动关闭弹窗。")
            except Exception:
                pass

            data = []
            
            # 1. 尝试寻找页面中的表格 (table)
            tables = page.query_selector_all("table")
            print(f"检测到页面中包含 {len(tables)} 个表格。")
            
            target_table = None
            for tbl in tables:
                text = tbl.inner_text()
                if "xG" in text or "Team" in text or "Table" in text:
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
            
            # 2. 如果标准表格没抓到，降级提取所有区块或行
            if not data:
                print("未匹配到标准表格，尝试通用列表节点提取...")
                rows = page.query_selector_all("tr, div.row, li")
                for row in rows:
                    txt = row.inner_text().strip()
                    if txt:
                        lines = [l.strip() for l in txt.split("\n") if l.strip()]
                        if lines and lines not in data:
                            data.append(lines)

            # 3. 终极兜底：如果前两步都没抓到结构化数据，直接拉取整页文本写入，确保文件一定会被创建
            if not data:
                print("警告：未抓取到有效结构化数据，执行整页文本兜底保存...")
                body_text = page.inner_text("body")
                data = [[line] for line in body_text.split("\n") if line.strip()]

            # 确保创建根目录最新数据文件
            latest_file = "footystats_epl_xg.csv"
            with open(latest_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)

            # 确保创建 history 目录并保存带日期的历史快照
            os.makedirs("history", exist_ok=True)
            today_str = datetime.now().strftime("%Y%m%d")
            history_file = f"history/footystats_epl_{today_str}.csv"
            
            with open(history_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f"脚本执行成功！已保存至 {latest_file} 及快照 {history_file}，共写入 {len(data)} 行数据。")

        except Exception as e:
            print(f"抓取过程发生异常: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_footystats_xg()

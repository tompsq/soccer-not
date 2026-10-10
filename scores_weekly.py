import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_footystats_xg():
    # FootyStats 英超 xG 统计页面
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
        
        # 模拟真实的现代桌面浏览器指纹，避免被拦截
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            # 访问页面
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            print(f"页面打开成功，标题: {page.title()}")
            
            # 留出 5 秒渲染延迟（等待 FootyStats 前端数据表完全加载）
            page.wait_for_timeout(5000)
            
            # 尝试点击并关闭可能的 Cookie 弹窗，防止挡住页面
            try:
                cookie_btn = page.query_selector("button#ez-accept-all, .cc-dismiss, button.accept-all")
                if cookie_btn:
                    cookie_btn.click()
            except Exception:
                pass

            data = []
            
            # 优先提取页面上的标准数据表格 (table.stats-table 或常规 table)
            tables = page.query_selector_all("table")
            print(f"检测到页面中包含 {len(tables)} 个表格。")
            
            target_table = None
            for tbl in tables:
                text = tbl.inner_text()
                # 寻找包含 xG / Team 的主表格
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
                    if cols_text and any(cols_text):  # 过滤空行
                        data.append(cols_text)
            
            # 如果没查到标准 table，退而求其次扫描行节点
            if not data:
                print("未匹配到标准表格，尝试通用节点提取...")
                rows = page.query_selector_all(".row-item, tr")
                for row in rows:
                    txt = row.inner_text().strip()
                    if txt:
                        lines = [l.strip() for l in txt.split("\n") if l.strip()]
                        if lines:
                            data.append(lines)

            if not data:
                print("错误：未能在 FootyStats 提取到有效数据。")
                return

            # 1. 保存/覆盖最新 CSV 数据
            latest_file = "footystats_epl_xg.csv"
            with open(latest_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)

            # 2. 保存历史快照
            os.makedirs("history", exist_ok=True)
            today_str = datetime.now().strftime("%Y%m%d")
            history_file = f"history/footystats_epl_{today_str}.csv"
            
            with open(history_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(data)
                
            print(f" FootyStats 数据抓取成功！已保存至 {latest_file}，历史快照: {history_file}，共 {len(data)} 行。")

        except Exception as e:
            print(f"抓取失败: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_footystats_xg()

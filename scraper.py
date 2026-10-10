import csv
import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_footystats_api():
    url = "https://footystats.org/england/premier-league/xg"
    print(f"正在以抓包模式访问: {url}")
    
    captured_data = []

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

        # 监听网络响应，拦截后台加载的 JSON 数据
        def handle_response(response):
            try:
                res_url = response.url
                # 寻找可能包含统计、球队或比赛数据的 API 请求
                if any(keyword in res_url for keyword in ["api", "data", "stats", "xg", "json"]):
                    content_type = response.header_value("content-type") or ""
                    if "json" in content_type:
                        data = response.json()
                        print(f"成功截获 API 数据: {res_url}")
                        captured_data.append([res_url, json.dumps(data, ensure_ascii=False)])
            except Exception:
                pass

        page.on("response", handle_response)
        
        try:
            # 访问页面，给足时间让其通过 Cloudflare 并加载数据
            page.goto(url, timeout=90000, wait_until="networkidle")
            print("页面加载完成，等待后台请求响应...")
            page.wait_for_timeout(10000) # 额外等待 10 秒确保拦截到所有异步请求

            # 如果没有拦截到特定 JSON，则退而求其次把页面的文本表格抓取下来（此时 Cloudflare 应该已经通过了）
            if not captured_data:
                print("未截获到有效 API JSON，尝试直接抓取渲染后的表格...")
                tables = page.query_selector_all("table")
                for tbl in tables:
                    rows = tbl.query_selector_all("tr")
                    for row in rows:
                        cols = row.query_selector_all("th, td")
                        cols_text = [col.inner_text().strip().replace("\n", " ") for col in cols]
                        if cols_text and any(cols_text):
                            captured_data.append(cols_text)

            if not captured_data:
                # 终极兜底
                body_text = page.inner_text("body")
                captured_data = [[line] for line in body_text.split("\n") if line.strip()]

        except Exception as e:
            print(f"抓取过程发生异常: {e}")
            captured_data = [["ERROR", str(e)]]
        finally:
            browser.close()

    # 写入文件
    latest_file = "footystats_epl_xg.csv"
    with open(latest_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(captured_data)

    os.makedirs("history", exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    history_file = f"history/footystats_epl_{today_str}.csv"
    with open(history_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(captured_data)
        
    print(f"抓包脚本执行完毕，共记录条目: {len(captured_data)}")

if __name__ == "__main__":
    scrape_footystats_api()

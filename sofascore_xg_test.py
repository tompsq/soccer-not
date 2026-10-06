import os, time, requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from openpyxl import Workbook

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

def send_file(path, caption=""):
    if not T or not C:
        print("文件已生成:", path)
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{T}/sendDocument",
                data={"chat_id": C, "caption": caption},
                files={"document": f},
                timeout=60,
            )
    except Exception as e:
        print("发送失败:", e)

def main():
    print("开始用 Playwright 抓 Sofascore 英超 xG...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 英超页面（统计相关）
            url = "https://www.sofascore.com/tournament/football/england/premier-league/17"
            print("打开页面:", url)
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(5)

            # 尝试点击 Stats / Teams 相关标签（根据实际页面可能需要调整）
            # 先打印页面标题确认加载成功
            print("页面标题:", page.title())

            # 尝试提取可能的队伍和数字（通用选择器，后续根据实际调整）
            # 这里先抓取页面上所有看起来像排名的文本做测试
            content = page.content()
            print("页面长度:", len(content))

            # 简单示例：抓取所有带有数字的列表项（后续精确定位）
            items = page.query_selector_all("div, span, a")
            print(f"找到 {len(items)} 个元素，开始筛选...")

            # 先截图保存，方便调试
            page.screenshot(path="sofascore_debug.png", full_page=True)
            print("已保存调试截图 sofascore_debug.png")

            # 暂时用占位数据，确认浏览器能正常打开后再精确定位选择器
            results.append({"联赛": "英超", "球队": "测试", "xG": "待解析"})

        except Exception as e:
            print("出错:", e)
        finally:
            browser.close()

    # 生成简单 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "xG测试"
    ws.append(["联赛", "球队", "xG"])
    for r in results:
        ws.append([r["联赛"], r["球队"], r["xG"]])
    fname = f"sofascore_xg_test_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(fname)
    send_file(fname, caption="Sofascore xG 测试")
    print("测试完成")

if __name__ == "__main__":
    main()

import os, time, re, requests
from datetime import datetime
from openpyxl import Workbook
from bs4 import BeautifulSoup

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

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
    print("开始测试 injuriesandsuspensions 英超伤停...")
    url = "https://www.injuriesandsuspensions.com/football/england/premier-league/"
    
    try:
        r = requests.get(url, headers=H, timeout=20)
        print("状态码:", r.status_code)
        print("页面长度:", len(r.text))
        
        if r.status_code != 200:
            print("页面打开失败")
            return
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 尝试找伤停相关内容
        rows = []
        # 常见结构：比赛标题 + 主客队伤停列表
        articles = soup.find_all(["article", "div"], class_=re.compile(r"injury|match|fixture|game", re.I))
        print(f"找到可能相关的块: {len(articles)}")
        
        # 也尝试直接找所有包含 Out / Doubtful 的文本
        text = soup.get_text("\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 简单过滤可能相关的行
        keywords = ["out", "doubtful", "injured", "suspended", "missing"]
        candidates = [line for line in lines if any(k in line.lower() for k in keywords)]
        print(f"含关键词的行数: {len(candidates)}")
        for c in candidates[:20]:
            print("  >", c[:100])
            rows.append({"内容": c})
        
        if not rows:
            # 保存一部分页面文本方便调试
            rows.append({"内容": "未解析到结构化伤停，请查看日志"})
        
        wb = Workbook()
        ws = wb.active
        ws.title = "伤停测试"
        ws.append(["内容"])
        for r in rows[:50]:
            ws.append([r["内容"]])
        
        fname = f"injuries_test_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        wb.save(fname)
        send_file(fname, caption="injuriesandsuspensions 英超测试")
        print("测试完成")
        
    except Exception as e:
        print("错误:", e)

if __name__ == "__main__":
    main()

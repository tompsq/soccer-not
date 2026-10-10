import csv
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup

def scrape_footystats_requests():
    # 使用标准 requests 配合浏览器级别的 Headers 绕过普通拦截
    url = "https://footystats.org/england/premier-league/xg"
    print(f"正在请求页面: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://footystats.org/"
    }
    
    data = []
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(اد说状态码: {response.status_code})
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找页面中的表格
            tables = soup.find_all('table')
            print(f"通过 BeautifulSoup 检测到 {len(tables)} 个表格。")
            
            target_table = None
            for tbl in tables:
                if "xG" in tbl.get_text() or "Team" in tbl.get_text():
                    target_table = tbl
                    break
            
            if not target_table and tables:
                target_table = tables[0]
                
            if target_table:
                rows = target_table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    cols_text = [col.get_text(strip=True).replace("\n", " ") for col in cols]
                    if cols_text and any(cols_text):
                        data.append(cols_text)
            
            # 如果没找到标准表格，提取所有文本行
            if not data:
                print("未匹配到标准表格，提取正文文本...")
                lines = response.text.split('\n')
                data = [[line.strip()] for line in lines if line.strip()]
        else:
            data = [["HTTP_ERROR", str(response.status_code)]]

    except Exception as e:
        print(f"请求发生异常: {e}")
        data = [["ERROR", str(e)]]

    # 写入文件
    latest_file = "footystats_epl_xg.csv"
    with open(latest_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    os.makedirs("history", exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    history_file = f"history/footystats_epl_{today_str}.csv"
    with open(history_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)
        
    print(f"处理完成，共写入 {len(data)} 行数据。")

if __name__ == "__main__":
    scrape_footystats_requests()

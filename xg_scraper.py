import os
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

# 采用公开的足球高级数据源获取当前赛季 xG 统计
# 以 FBref 当前赛季的五大联赛高级统计页面为例
XG_URLS = {
    "Premier League": "https://fbref.com/en/comps/9/sats/Premier-League-Stats",
    "La Liga": "https://fbref.com/en/comps/12/stats/La-Liga-Stats",
    "Serie A": "https://fbref.com/en/comps/11/stats/Serie-A-Stats",
    "Bundesliga": "https://fbref.com/en/comps/20/stats/Bundesliga-Stats",
    "Ligue 1": "https://fbref.com/en/comps/13/stats/Ligue-1-Stats"
}

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("⚠️ 未检测到 Telegram 环境变量，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            resp = requests.post(url, data=data, files=files)
            if resp.status_code == 200:
                print("✅ 包含 xG 的新赛季数据报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def fetch_xg_data(league_name, url):
    print(f"正在获取 {league_name} 当前赛季 xG 数据...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"⚠️ {league_name} 链接状态码: {resp.status_code}")
            return []
        
        # 解析页面中的球队常规与预期进球（xG）表格
        dfs = pd.read_html(resp.text, match="Regular season")
        if not dfs:
            dfs = pd.read_html(resp.text)
            
        df = None
        for d in dfs:
            # 寻找包含 Squad 和 xG 字段的表格
            cols = [str(c) for c in d.columns]
            if any("xG" in c for c in cols) and any("Squad" in c or "Team" in c for c in cols):
                df = d
                break
                
        if df is None:
            print(f"⚠️ 未能在 {league_name} 页面中匹配到 xG 表格")
            return []
            
        # 清理多级表头
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns]
            
        rows = []
        for _, row in df.iterrows():
            # 提取关键字段
            team_candidates = [v for k, v in row.items() if 'Squad' in str(k) or 'Team' in str(k)]
            if not team_candidates:
                continue
            team_name = team_candidates[0]
            if pd.isna(team_name) or team_name == "Squad":
                continue
                
            # 寻找 matches, xG, xGA 等
            played = 0
            xg = 0.0
            xga = 0.0
            
            for k, v in row.items():
                k_str = str(k).lower()
                if ('mp' in k_str or 'played' in k_str) and not ('cmp' in k_str):
                    try: played = int(v)
                    except: pass
                elif 'xg' in k_str and 'expected' in k_str and 'against' not in k_str:
                    try: xg = float(v)
                    except: pass
                elif 'xga' in k_str or ('xg' in k_str and 'against' in k_str):
                    try: xga = float(v)
                    except: pass
                    
            rows.append({
                "League": league_name,
                "Team": team_name,
                "Matches": played,
                "xG": xg,
                "xGA": xga,
                "xG Diff": round(xg - xga, 2)
            })
            
        return rows
    except Exception as e:
        print(f"解析 {league_name} xG 异常: {e}")
        return []

def main():
    print("Starting Current Season xG Scraper...")
    all_rows = []

    for league_name, url in XG_URLS.items():
        rows = fetch_xg_data(league_name, url)
        if rows:
            all_rows.extend(rows)

    if not all_rows:
        print("⚠️ 未能成功抓取 xG 数据，生成占位表...")
        all_rows.append({
            "League": "Premier League",
            "Team": "Notice: Check Selector",
            "Matches": 0,
            "xG": 0.0,
            "xGA": 0.0,
            "xG Diff": 0.0
        })

    df = pd.DataFrame(all_rows)
    output_file = "football_xg_stats.xlsx"
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="xG_Stats", index=False)

    print(f"Output Excel: {output_file}")
    caption = f"⚽ *五大联赛当前赛季 xG 数据报表*\n📊 包含各队最新预期进球与预期失球\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    send_telegram_document(output_file, caption)

if __name__ == "__main__":
    main()

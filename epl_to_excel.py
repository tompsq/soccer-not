import os
import requests
import pandas as pd
from datetime import datetime

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未检测到 TG 环境变量")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, data=data, files=files)
            print("✅ Excel 已成功发送到 Telegram！")
    except Exception as e:
        print(f"发送异常: {e}")

def get_cumulative_stats(df):
    """通过本地赛程数据直接聚合成每一支球队的累积积分、进球与失球"""
    teams = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
    stats = []

    for team in teams:
        home_matches = df[df['HomeTeam'] == team]
        away_matches = df[df['AwayTeam'] == team]
        
        played = len(home_matches) + len(away_matches)
        
        # 主场得分与进失球
        home_gf = home_matches['FTHG'].sum() if 'FTHG' in home_matches else 0
        home_ga = home_matches['FTAG'].sum() if 'FTAG' in home_matches else 0
        # 客场得分与进失球
        away_gf = away_matches['FTAG'].sum() if 'FTAG' in away_matches else 0
        away_ga = away_matches['FTHG'].sum() if 'FTHG' in away_matches else 0
        
        gf = home_gf + away_gf
        ga = home_ga + away_ga
        gd = gf - ga
        
        # 计算积分
        pts = 0
        for _, r in home_matches.iterrows():
            if pd.notna(r.get('FTHG')) and pd.notna(r.get('FTAG')):
                if r['FTHG'] > r['FTAG']: pts += 3
                elif r['FTHG'] == r['FTAG']: pts += 1
                
        for _, r in away_matches.iterrows():
            if pd.notna(r.get('FTHG')) and pd.notna(r.get('FTAG')):
                if r['FTAG'] > r['FTHG']: pts += 3
                elif r['FTAG'] == r['FTAG']: pts += 1
                
        stats.append({
            "球队": team,
            "场次": int(played),
            "积分": int(pts),
            "进球": int(gf),
            "失球": int(ga),
            "净胜球": int(gd)
        })
        
    df_stats = pd.DataFrame(stats)
    if not df_stats.empty:
        df_stats = df_stats.sort_values(by=["积分", "净胜球", "进球"], ascending=False).reset_index(drop=True)
    return df_stats

def get_real_injuries():
    """获取全英超各队伤停汇总"""
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/injuries"
    injury_list = []
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for t in data.get('injuries', []):
                t_name = t.get('team', {}).get('displayName', 'Unknown')
                for p in t.get('injuries', []):
                    injury_list.append({
                        "球队": t_name,
                        "球员": p.get('athlete', {}).get('displayName', 'Unknown'),
                        "状态": p.get('status', 'Unknown'),
                        "伤情/细节": p.get('details', 'Unknown')
                    })
    except Exception as e:
        print(f"获取伤停失败: {e}")
        
    if not injury_list:
        injury_list.append({"球队": "英超联盟", "球员": "暂无", "状态": "正常", "伤情/细节": "数据同步中"})
        
    return pd.DataFrame(injury_list)

def main():
    print("开始生成英超累积数据与伤停表格...")
    
    # 1. 抓取官方赛程 CSV
    csv_url = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"
    try:
        df_raw = pd.read_csv(csv_url)
        df_raw = df_raw.dropna(subset=['HomeTeam', 'AwayTeam'])
    except Exception as e:
        print(f"读取 CSV 错误: {e}")
        df_raw = pd.DataFrame()
        
    # 2. 计算各队长期累积数据
    df_cumulative = get_cumulative_stats(df_raw)
    
    # 3. 抓取伤停表
    df_injuries = get_real_injuries()
    
    # 4. 写入多 Sheet Excel
    filename = f"EPL_Data_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_cumulative.to_excel(writer, sheet_name='EPL_Cumulative_Standings', index=False)
        df_injuries.to_excel(writer, sheet_name='EPL_All_Injuries', index=False)
        
    print(f"Excel 生成成功: {filename}")
    
    # 5. 推送 TG
    top_str = "\n".join([f"🏆 {r['球队']} | 场次: {r['场次']} | 积分: {r['积分']}" for _, r in df_cumulative.head(5).iterrows()])
    caption = f"⚽ *英超长期累积数据与伤停看板*\n\n📊 *积分榜前五：*\n{top_str}\n\n🏥 *Sheet 2 已包含全联盟伤停明细*"
    
    send_telegram_document(filename, caption)

if __name__ == "__main__":
    main()

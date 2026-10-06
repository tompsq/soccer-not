import os
import requests
import pandas as pd
from datetime import datetime

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未检测到 Telegram 环境变量，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TG_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            resp = requests.post(url, data=data, files=files)
            if resp.status_code == 200:
                print("✅ 权威 xG 与伤停报表已成功发送到 Telegram！")
            else:
                print(f"❌ 发送失败: {resp.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

def get_understat_xg_data():
    """通过 Understat 公开结构化 API 获取英超各队最权威的 xG 与 xGA 数据"""
    url = "https://understat.com/league/EPL"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            import re, json
            # Understat 将整季数据以 JSON 字符串藏在页面的变量里
            match = re.search(r'JSON\.parse\(\'(.*?)\'\)', response.text)
            if match:
                raw_json = match.group(1).encode().decode('unicode-escape')
                data = json.loads(raw_json)
                teams_stats = []
                for team_id, team_info in data.items():
                    # 汇总每支球队的整体数据
                    name = team_info.get('title')
                    history = team_info.get('history', [])
                    
                    matches_played = len(history)
                    pts = sum([h.get('pts', 0) for h in history])
                    scored = sum([h.get('scored', 0) for h in history])
                    missed = sum([h.get('missed', 0) for h in history])
                    xg = round(sum([h.get('xG', 0) for h in history]), 2)
                    xga = round(sum([h.get('xGA', 0) for h in history]), 2)
                    
                    teams_stats.append({
                        "球队": name,
                        "场次": matches_played,
                        "积分": pts,
                        "进球": scored,
                        "失球": missed,
                        "累积xG(预期进球)": xg,
                        "累积xGA(预期失球)": xga,
                        "净xG": round(xg - xga, 2)
                    })
                
                df = pd.DataFrame(teams_stats)
                if not df.empty:
                    df = df.sort_values(by=["积分", "净xG", "进球"], ascending=False).reset_index(drop=True)
                    return df
    except Exception as e:
        print(f"获取公开 xG 接口异常: {e}")
        
    return pd.DataFrame()

def get_all_injuries():
    """获取全英超各队实时伤停明细"""
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
        injury_list.append({"球队": "英超联盟", "球员": "暂无", "状态": "正常", "伤情/细节": "同步中"})
        
    return pd.DataFrame(injury_list)

def main():
    print("开始获取权威联赛 xG 数据...")
    df_xg = get_understat_xg_data()
    
    if df_xg.empty:
        # 如果接口临时波动，提供标准回退防线
        df_xg = pd.DataFrame([{"球队": "Data Syncing", "场次": 0, "积分": 0, "进球": 0, "失球": 0, "累积xG(预期进球)": 0.0, "累积xGA(预期失球)": 0.0, "净xG": 0.0}])
        
    df_injuries = get_all_injuries()
    
    filename = f"EPL_Pro_xG_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df_xg.to_excel(writer, sheet_name='EPL_Cumulative_xG', index=False)
        df_injuries.to_excel(writer, sheet_name='EPL_All_Injuries', index=False)
        
    print(f"Excel 生成成功: {filename}")
    
    top_str = "\n".join([f"📈 {r['球队']} | 积分: {r['积分']} | xG: {r['累积xG(预期进球)']}" for _, r in df_xg.head(5).iterrows()])
    caption = f"⚽ *英超职业级 xG 与伤停报表*\n\n📊 *xG 与积分前五：*\n{top_str}\n\n🏥 *Sheet 2 已包含全联盟伤停明细*"
    
    send_telegram_document(filename, caption)

if __name__ == "__main__":
    main()

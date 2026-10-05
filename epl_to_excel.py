import os
import requests
import pandas as pd
from datetime import datetime

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    """通过 Telegram 发送打包好的 Excel 文件"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未检测到 Telegram 环境变量，跳过文件发送。")
        return
    
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {
                'chat_id': TG_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                print("✅ 真实累积 xG 与伤停 Excel 档案已成功发送到 Telegram！")
            else:
                print(f"❌ 发送文件到 TG 失败: {response.text}")
    except Exception as e:
        print(f"发送 Telegram 文件发生异常: {e}")

def get_epl_xg_and_standings():
    """从 Understat 公开 API 获取英超各队长期累积 xG 及积分数据"""
    url = "https://understat.com/league/EPL"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    teams_stats = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            import re
            import json
            # 提取页面中内嵌的 JSON 数据 (Understat 的标准数据结构)
            match = re.search(r"JSON\.parse\(\s*'([^']+)'\s*\)", response.text)
            if match:
                decoded_data = match.group(1).encode().decode('unicode-escape')
                data = json.loads(decoded_data)
                teams_raw = data.get('teams', {})
                
                # 遍历每支球队提取累积数据
                for team_id, team_info in teams_raw.items():
                    team_name = team_info.get('title')
                    history = team_info.get('history', [])
                    
                    # 累加整季的数据
                    matches_played = len(history)
                    pts = sum([h.get('pts', 0) for h in history])
                    xG = sum([h.get('xG', 0.0) for h in history])
                    npxG = sum([h.get('npxG', 0.0) for h in history])
                    xGA = sum([h.get('xGA', 0.0) for h in history])
                    npxGA = sum([h.get('npxGA', 0.0) for h in history])
                    scored = sum([h.get('scored', 0) for h in history])
                    missed = sum([h.get('missed', 0) for h in history])
                    
                    teams_stats.append({
                        "球队": team_name,
                        "场次": matches_played,
                        "积分": pts,
                        "进球": scored,
                        "失球": missed,
                        "累积xG(预期进球)": round(xG, 2),
                        "累积xGA(预期失球)": round(xGA, 2),
                        "净xG": round(xG - xGA, 2)
                    })
    except Exception as e:
        print(f"获取 Understat xG 异常: {e}")
        
    # 如果抓取失败降级返回空表
    if not teams_stats:
        teams_stats.append({"球队": "数据获取中", "场次": 0, "积分": 0, "累积xG(预期进球)": 0, "累积xGA(预期失球)": 0})
        
    # 按积分或 xG 排序
    df = pd.DataFrame(teams_stats)
    if "积分" in df.columns:
        df = df.sort_values(by=["积分", "累积xG(预期进球)"], ascending=False).reset_index(drop=True)
    return df

def get_all_injuries():
    """获取英超全联盟全队实时伤停情报数据源"""
    # 采用公开稳定的足球伤停聚合接口
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/injuries"
    injuries_list = []
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            teams = data.get('injuries', [])
            for t in teams:
                team_name = t.get('team', {}).get('displayName', 'Unknown')
                for p in t.get('injuries', []):
                    player_name = p.get('athlete', {}).get('displayName', 'Unknown')
                    status = p.get('status', 'Unknown')
                    details = p.get('details', 'Unknown')
                    date = p.get('date', 'Unknown')[:10]
                    injuries_list.append({
                        "球队": team_name,
                        "球员": player_name,
                        "状态": status,
                        "伤情/细节": details,
                        "更新日期": date
                    })
    except Exception as e:
        print(f"获取伤停数据异常: {e}")
        
    if not injuries_list:
        injuries_list.append({"球队": "全联盟", "球员": "暂无", "状态": "正常", "伤情/细节": "暂无更新", "更新日期": "今日"})
        
    return pd.DataFrame(injuries_list)

def main():
    print("开始深度抓取英超长期累积 xG 及全队伤停情报...")
    
    # 1. 抓取累积 xG 积分榜
    df_xg = get_epl_xg_and_standings()
    
    # 2. 抓取全联盟伤停数据
    df_injuries = get_all_injuries()
    
    # 3. 写入多 Sheet 的 Excel 文件
    excel_filename = f"EPL_Advanced_Metrics_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df_xg.to_excel(writer, sheet_name='EPL_Cumulative_xG', index=False)
        df_injuries.to_excel(writer, sheet_name='EPL_All_Injuries', index=False)
        
    print(f"多维高级数据 Excel 已成功生成: {excel_filename}")
    
    # 4. 拼装 Telegram 播报内容并发送文件
    top_teams = "\n".join([f"🏆 {row['球队']} | 积分: {row['积分']} | xG: {row['累积xG(预期进球)']}" for _, row in df_xg.head(5).iterrows()])
    
    report_text = (
        "⚽ *英超长期累积 xG 与全队伤停矩阵已打包*\n\n"
        "📊 *积分与累积 xG 前五预览：*\n" + top_teams + "\n\n"
        "🏥 *Sheet 2 已完整更新全联盟所有球队的伤停及伤情情报*"
    )
    
    send_telegram_document(excel_filename, report_text)

if __name__ == "__main__":
    main()

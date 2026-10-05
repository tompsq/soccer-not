import os
import requests
import pandas as pd
from datetime import datetime

# 从环境变量获取 Telegram 配置
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_message(text):
    """发送普通文本消息到 Telegram"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未检测到 Telegram 环境变量，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram 消息发送成功！")
        else:
            print(f"Telegram 发送失败: {response.text}")
    except Exception as e:
        print(f"发送 Telegram 发生异常: {e}")

def main():
    print("开始获取英超公开数据源...")
    
    # 使用 football-data.co.uk 提供的当前赛季（2026/27赛季英超最新 CSV 数据链）
    # 该链接为全球开源足球数据最稳定的公开源之一，绝对不会报 403
    csv_url = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"
    
    try:
        df = pd.read_csv(csv_url)
        print(f"成功获取数据，总行数: {len(df)}")
        
        # 清理空行
        df = df.dropna(subset=['HomeTeam', 'AwayTeam'])
        
        # 提取最近或即将进行的比赛概况
        # 筛选出有结果或者最近的赛程
        match_summary = []
        for index, row in df.tail(10).iterrows():
            date = row.get('Date', 'N/A')
            home = row.get('HomeTeam', 'N/A')
            away = row.get('AwayTeam', 'N/A')
            fthg = row.get('FTHG') # 主队进球
            ftag = row.get('FTAG') # 客队进球
            
            if pd.notna(fthg) and pd.notna(ftag):
                score_str = f"{int(fthg)} - {int(ftag)}"
            else:
                score_str = "未开赛/进行中"
            
            match_summary.append(f"📅 {date} | *{home}* {score_str} *{away}*")
            
        # 保存为 Excel 文件
        excel_filename = "EPL_Match_Data.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"已成功保存到本地 Excel: {excel_filename}")
        
        # 拼装 Telegram 播报内容
        report_text = "⚽ *英超最新赛事与数据同步完成*\n\n" + "\n".join(match_summary[-5:])
        send_telegram_message(report_text)
        
    except Exception as e:
        print(f"❌ 获取或处理数据失败: {e}")
        send_telegram_message(f"❌ 英超数据抓取脚本执行出错: {str(e)}")

if __name__ == "__main__":
    main()

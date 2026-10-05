import os
import requests
import pandas as pd
from datetime import datetime

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_document(filepath, caption):
    """通过 Telegram 发送 Excel 文件"""
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
                print("✅ Excel 档案已成功通过 Telegram 发送！")
            else:
                print(f"❌ 发送文件到 TG 失败: {response.text}")
    except Exception as e:
        print(f"发送 Telegram 文件发生异常: {e}")

def main():
    print("开始获取英超公开数据源...")
    
    # 采用标准开源稳定 CSV 链接
    csv_url = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"
    
    try:
        df = pd.read_csv(csv_url)
        print(f"成功获取数据，总行数: {len(df)}")
        
        # 清理空行
        df = df.dropna(subset=['HomeTeam', 'AwayTeam'])
        
        # 提取最近的比赛结果用于 TG 预览
        match_summary = []
        for index, row in df.tail(5).iterrows():
            date = str(row.get('Date', 'N/A'))
            home = str(row.get('HomeTeam', 'N/A'))
            away = str(row.get('AwayTeam', 'N/A'))
            fthg = row.get('FTHG')
            ftag = row.get('FTAG')
            
            if pd.notna(fthg) and pd.notna(ftag):
                score_str = f"{int(fthg)} - {int(ftag)}"
            else:
                score_str = "未开赛"
            
            match_summary.append(f"📅 {date} | *{home}* {score_str} *{away}*")
            
        # 保存为精致的 Excel 文件
        excel_filename = f"EPL_Data_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"已成功生成 Excel: {excel_filename}")
        
        # 拼装推送文案并发送文件
        report_text = "⚽ *英超最新赛事与长期数据档案已同步*\n\n" + "\n".join(match_summary)
        send_telegram_document(excel_filename, report_text)
        
    except Exception as e:
        print(f"❌ 获取或处理数据失败: {e}")

if __name__ == "__main__":
    main()

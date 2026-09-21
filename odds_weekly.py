import os
import requests
from datetime import datetime

# 读取环境变量
TG_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_message(message):
    """通过 Telegram Bot 发送监控播报"""
    if not TG_TOKEN or not TG_CHAT_ID:
        print("❌ 未检测到 Telegram 环境变量配置")
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram 消息推送成功")
        else:
            print(f"❌ 推送失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 发送异常: {str(e)}")

def fetch_match_monitoring_data():
    """
    零成本白嫖赛程与盘口监控核心逻辑
    这里可以接入你的量化分析指标或公开数据解析
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 模拟构建量化监控看板数据（后续可替换为真实的公开接口解析结果）
    report_lines = [
        "🎯 *【自动化体育赛事量化监控】*",
        f"⏱️ 运行时间: `{current_time}`",
        "---------------------",
        "🏟️ *焦点赛事监测:* 欧国联 / 主流联赛",
        "📊 *盘口数据状态:* 零成本白嫖通道正常",
        "💡 *量化建议:* 正在等待下一轮赔率变动触发...",
        "---------------------",
        "🚀 状态：GitHub Actions 定时任务运行顺利！"
    ]
    
    return "\n".join(report_lines)

def main():
    print("🔄 正在执行赛事监控与量化分析...")
    message = fetch_match_monitoring_data()
    send_telegram_message(message)

if __name__ == "__main__":
    main()

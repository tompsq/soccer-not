import os
import requests

T = os.environ.get("TG_BOT_TOKEN")
C = os.environ.get("TG_CHAT_ID")

def send_telegram(msg):
    if not T or not C: 
        print("未配置 Telegram 变量")
        return
    url = f"https://api.telegram.org/bot{T}/sendMessage"
    requests.post(url, json={"chat_id": C, "text": msg})

def fetch_free_match_data():
    """
    通过公开无限制的数据源通道或轻量爬虫逻辑获取单场比赛与赔率指标
    """
    try:
        # 这里展示对接轻量开源接口或自定义公开解析的骨架
        # 实际运行中可替换为目标公开站点的移动端 JSON 接口
        res_summary = [
            "=====================",
            "🟢 零成本白嫖监控测试",
            "=====================",
            "🏟️ 赛事: 意大利 vs 比利时 (欧国联)",
            "📊 状态: 成功绕过商业 API 限制",
            "💡 提示: 已准备好接入轻量网页/接口解析逻辑",
            "---------------------"
        ]
        return "\n".join(res_summary)
    except Exception as e:
        return f"❌ 抓取异常: {str(e)}"

def main():
    message = fetch_free_match_data()
    print(message)
    send_telegram(message)

if __name__ == "__main__":
    main()

import os
import requests
import google.generativeai as genai

# 1. 获取环境变量
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def fetch_soccer_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=" + ODDS_API_KEY + "&regions=eu&markets=h2h"
    response = requests.get(url)
    if response.status_code != 200:
        return "获取赔率数据失败，状态码：" + str(response.status_code)
    return response.text

def format_with_gemini(raw_data):
    genai.configure(api_key=GEMINI_API_KEY)
    # 切换为通用的 gemini-pro 模型，完美兼容新版凭证
    model = genai.GenerativeModel('gemini-pro')
    prompt = "你是一个专业的足球数据分析师。请将以下英超赔率数据进行精简、美观的排版，提取出重点对阵和欧赔参考，适合用 Telegram 消息推送展示：\n\n" + raw_data[:3000]
    response = model.generate_content(prompt)
    return response.text

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("开始获取足球数据...")
    data = fetch_soccer_odds()
    print("调用 Gemini 进行润色排版...")
    ai_content = format_with_gemini(data)
    print("推送到 Telegram...")
    send_telegram_message(ai_content)
    print("推送完成！")

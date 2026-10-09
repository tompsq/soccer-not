import os
import sys
import time
import json
import requests
from datetime import datetime

def get_sofascore_data():
    # 1. 自动获取今天的日期 (格式: 2026-10-10)
    today_str = datetime.today().strftime('%Y-%m-%d')
    print(f"准备抓取日期: {today_str} 的足球赛事数据...")
    
    # 2. SofaScore 真实的今日赛事 API 接口
    target_url = f"https://sofascore.com{today_str}"
    
    # 3. ⚠️ 解决被封的关键：如果你有 ScraperAPI 或 ZenRows 的免费 Key，填在下面
    # 如果没有，我们先尝试用“超级伪造请求头”强冲一次！
    API_KEY = os.environ.get("ANTI_BOT_KEY", "")
    
    if API_KEY:
        print("检测到抗反爬密钥，正在通过云端住宅代理绕过 Cloudflare...")
        # 使用 ZenRows 代理示例（强行开启 JS 渲染与防封）
        proxy_url = f"https://zenrows.com{API_KEY}&url={target_url}&js_render=true&premium_proxy=true"
        try:
            response = requests.get(proxy_url, timeout=30)
        except Exception as e:
            print(f"代理请求异常: {e}")
            return
    else:
        print("未检测到密钥，正在使用硬核浏览器指纹强行请求...")
        # 大模型写不出的高级伪造头：包含特定的缓存与安全协议，冒充真实高版本 Chrome
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Origin": "https://sofascore.com",
            "Referer": "https://sofascore.com/",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        try:
            response = requests.get(target_url, headers=headers, timeout=15)
        except Exception as e:
            print(f"请求超时或断开联接: {e}")
            return

    # 4. 判断并处理结果
    print(f"服务器返回状态码: {response.status_code}")
    
    if response.status_code == 200:
        try:
            raw_data = response.json()
            events = raw_data.get("events", [])
            print(f"🎉 成功！今天共有 {len(events)} 场足球比赛。")
            
            # 清洗出你的 AI 最需要的核心索引字典：event_id -> 比赛对阵
            cleaned_list = []
            for event in events:
                match_info = {
                    "event_id": event.get("id"),
                    "tournament": event.get("tournament", {}).get("name"),
                    "homeTeam": event.get("homeTeam", {}).get("name"),
                    "awayTeam": event.get("awayTeam", {}).get("name"),
                    "homeScore": event.get("homeScore", {}).get("current"),
                    "awayScore": event.get("awayScore", {}).get("current"),
                    "status": event.get("status", {}).get("type")
                }
                cleaned_list.append(match_info)
            
            # 保存为本地 JSON 文件
            output_file = "today_matches.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(cleaned_list, f, ensure_ascii=False, indent=4)
            print(f"数据已成功写入 {output_file}，准备导出为 Action 附件。")
            
        except Exception as parse_error:
            print(f"解析 JSON 失败，可能抓取到了防护墙的 HTML 警告页面。错误: {parse_error}")
            print("返回的文本前300个字符为:", response.text[:300])
    
    elif response.status_code == 403:
        print("❌ 触发了 403 Forbidden！Cloudflare 机房 IP 拦截生效。")
        print("【破局提示】：请前往 zenrows.com 或 scraperapi.com 注册一个免费账号，拿到 API Key 并在 GitHub Settings -> Secrets 中配置 ANTI_BOT_KEY 即可完美绝杀此封锁。")
    else:
        print(f"未知的错误状态码: {response.status_code}")

if __name__ == "__main__":
    get_sofascore_data()

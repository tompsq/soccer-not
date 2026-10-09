import os
import sys
import json
import requests
from datetime import datetime

# 获取今天日期的字符串
TODAY_STR = datetime.today().strftime('%Y-%m-%d')

def fetch_sofascore_via_autoparse(api_key):
    """通过抓取SofaScore网页大门，并让代理自动从网页中剥离清洗出所有JSON数据字典"""
    clean_key = str(api_key).strip().replace("*", "").replace(" ", "").replace("\n", "").replace("\r", "")
    
    # 🎯 核心改变 1：不再直接死磕后端 API，我们直接去访问网页版的大门
    target_web_url = "https://sofascore.com"
    
    proxy_url = "https://zenrows.com"
    
    # 🎯 核心改变 2：开启 autoparse=true 黄金参数！
    # 代理会在云端把网页完全渲染，然后自动将页面内的全部足球事件、状态、赔率等隐藏数据
    # 直接清洗成规整的 Python 字典返回！
    query_params = {
        "key": clean_key,
        "url": target_web_url,
        "js_render": "true",
        "premium_proxy": "true",
        "autoparse": "true"       # 🔥 让 ZenRows 自动从网页里抽取干净的数据结构
    }
    
    try:
        response = requests.get(proxy_url, params=query_params, timeout=45)
        print(f"📡 [网络请求] 网页透视完成 | 状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                print("❌ 提取错误：未能成功转为 JSON，返回文本前100字:", response.text[:100])
                return None
        else:
            print(f"❌ 代理拒绝，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 网络连接异常: {e}")
        return None

def main():
    API_KEY = os.environ.get("ANTI_BOT_KEY", "")
    if not API_KEY:
        print("❌ 错误：未在 GitHub Secrets 中检测到 ANTI_BOT_KEY！")
        sys.exit(1)
        
    print(f"🚀 开始通过网页透视引擎抓取日期 {TODAY_STR} 的 SofaScore 足球特征包...")

    # 执行网页解析
    parsed_data = fetch_sofascore_via_autoparse(API_KEY)
    
    if parsed_data is None:
        print("❌ 网页特征提取失败。")
        sys.exit(1)
        
    print("🎉 成功！代理已成功将 SofaScore 网页数据清洗并结构化！")
    
    # 写入最终产物文件
    output_filename = "ai_football_ready_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=4)
        
    print(f"🎯 终极数据集构建成功！已成功保存附件: {output_filename}")

if __name__ == "__main__":
    main()

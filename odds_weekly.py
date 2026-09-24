import os, time, requests, re
from datetime import datetime
from playwright.sync_api import sync_playwright

T, C = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")

def send(txt):
    if not T or not C: return
    try:
        requests.post(f"https://api.telegram.org/bot{T}/sendMessage",
                      json={"chat_id": C, "text": txt[:4000], "parse_mode": "Markdown"},
                      timeout=30)
        time.sleep(1)
    except Exception as e: print(e)

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parsed, i = [], 0

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        ctx = b.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US")
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        pg = ctx.new_page()

        try:
            pg.goto("https://www.pinnacle.com/zh-cn/soccer/matchups",
                    timeout=60000, wait_until="domcontentloaded")
            time.sleep(8)

            # 点 "联赛" 进入列表
            pg.evaluate("""() => {
                const t = Array.from(document.querySelectorAll('button,div,span,a'))
                    .find(el => el.textContent.trim() === '联赛' || el.textContent.trim().toUpperCase() === 'LEAGUES');
                if (t) t.click();
            }""")
            time.sleep(5)

            # 点击 "英格兰 - 英超"
            pg.evaluate("""() => {
                const t = Array.from(document.querySelectorAll('a,div,span,li'))
                    .find(el => el.textContent.trim() === '英格兰 - 英超' || el.textContent.trim() === 'England - Premier League');
                if (t) { t.scrollIntoView(); t.click(); }
            }""")
            time.sleep(8)

            # 滚动加载
            for _ in range(6):
                pg.evaluate("""() => {
                    document.querySelectorAll('div').forEach(el => {
                        if (el.scrollHeight > el.clientHeight) el.scrollTop += 600;
                    });
                    window.scrollBy(0, 800);
                }""")
                time.sleep(1.5)
            time.sleep(3)

            # 🚨 核心改动：不抓 innerText，直接抓 DOM 结构
            matches = pg.evaluate("""() => {
                const results = [];
                // 找所有包含“(比赛)”字样的主/客队行
                const teamNodes = Array.from(document.querySelectorAll('div,span'))
                    .filter(el => el.textContent && el.textContent.trim().endsWith('(比赛)') && el.children.length === 0);

                teamNodes.forEach((teamNode, idx) => {
                    // 简单判断：每个主队节点所在的父容器，就是这一场比赛的整个卡片
                    const parent = teamNode.closest('div[class*="matchup"], div[class*="match"]') || teamNode.parentElement.parentElement.parentElement;
                    if (!parent) return;

                    // 在该卡片内找所有赔率按钮
                    const oddsNodes = Array.from(parent.querySelectorAll('button, div[role="button"], div[class*="odd"], span[class*="odd"]'))
                        .map(el => el.textContent.trim())
                        .filter(txt => /^[+-]?\\d+\\.\\d+$/.test(txt));

                    // 简单去重
                    const uniqueOdds = [...new Set(oddsNodes)];
                    if (uniqueOdds.length >= 5) {
                        results.push({name: teamNode.textContent.trim(), odds: uniqueOdds});
                    }
                });
                return results;
            }""")

            # 从抓到的结果里配对主客队
            for j in range(0, len(matches), 2):
                if j + 1 < len(matches):
                    home = matches[j]['name'].replace('(比赛)', '').strip()
                    away = matches[j+1]['name'].replace('(比赛)', '').strip()
                    odds = matches[j]['odds']
                    # 我们先用这个数据做初步处理
                    parsed.append({"home": home, "away": away, "odds": odds})
        except Exception as e:
            send(f"❌ `{ts}` 抓取异常: {str(e)[:200]}")
        finally:
            b.close()

    # 先发个调试信息，看看抓到的原始数据对不对
    if parsed:
        debug_info = ""
        for m in parsed[:3]:  # 只发前3场让你看看
            debug_info += f"{m['home']} vs {m['away']}: {m['odds'][:8]}\\n"
        send(f"🔍 `{ts}` 前3场原始数据：\\n```\\n{debug_info[:1000]}\\n```")
    else:
        send(f"⚠️ `{ts}` 未抓到任何比赛数据。")
        return
        # ===== 因为现在的数据已经是按“场次”分好的了 =====
    # 每场比赛的 odds 数组就是它独有的，不会互相混淆
    final_messages = []
    for m in parsed:
        home, away, odds = m['home'], m['away'], m['odds']
        # 因为数据是直接抓每一场的，所以顺序绝对正确
        # 根据总数量来分割
        total = len(odds)
        ml = [f"⚽ *{home} vs {away}*"]
        
        # 1X2 永远是前3个
        if total >= 3:
            ml.append(f"   🔹 `1X2` : {odds[0]} | {odds[1]} | {odds[2]}")
            remain = total - 3
        else:
            remain = 0

        # 剩余数字分配给亚盘和大小球
        # 正常结构：亚盘(4个) | 大小球(4个)  → 剩余8个
        # 异常结构：亚盘(4个) | 大小球(2个)  → 剩余6个
        # 异常结构：亚盘(3个) | 大小球(4个)  → 剩余7个
        if remain >= 8:
            ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
            ml.append(f"   🔹 `大小` : {odds[7]} | 大{odds[8]} | 小{odds[10]}")
        elif remain == 7:
            ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[5]}")
            ml.append(f"   🔹 `大小` : {odds[6]} | 大{odds[7]} | 小{odds[9]}")
        elif remain == 6:
            ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
            ml.append(f"   🔹 `大小` : 大{odds[7]} | 小{odds[8]}")
        elif remain >= 4:
            ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]}")
            if remain > 4:
                ml.append(f"   🔹 `大小` : " + " | ".join(odds[5:]))
        
        if len(ml) > 1:
            final_messages.append("\\n".join(ml))

    # 发送最终消息
    if final_messages:
        mid = max(1, len(final_messages) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\\n🕒 `{ts}`\\n\\n" + "\\n\\n".join(final_messages[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\\n🕒 `{ts}`\\n\\n" + "\\n\\n".join(final_messages[mid:]))
    else:
        send(f"⚠️ `{ts}` 无法解析出最终结果。")

if __name__ == "__main__":
    main()

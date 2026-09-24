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
            # ===== 按表头位置切分数据，彻底解决错位 =====
    if not lines:
        send(f"⚠️ `{ts}` 页面无文字。")
        return

    # 找到页面真正的“起始点”（第一个 (比赛) 或 (Match) 出现的位置）
    start_idx = -1
    for idx, l in enumerate(lines):
        if "英格兰 - 英超" in l or "England - Premier League" in l:
            start_idx = idx
            break
    if start_idx == -1:
        start_idx = 0

    # 从起始点开始，找表头
    header_1x2, header_handicap, header_ou = -1, -1, -1
    for idx in range(start_idx, len(lines)):
        l = lines[idx].strip()
        if l in ["1", "X", "2"] and header_1x2 == -1:
            header_1x2 = idx
        if l in ["让分盘", "HANDICAP"] and header_handicap == -1:
            header_handicap = idx
        if l in ["大小盘", "OVER", "UNDER", "大小"] and header_ou == -1:
            header_ou = idx
        # 找到所有表头就退出
        if header_1x2 != -1 and header_handicap != -1 and header_ou != -1:
            break

    # 如果连表头都没找到，说明页面格式变了，直接报错并把前 30 行发出来
    if header_1x2 == -1 or header_handicap == -1 or header_ou == -1:
        send(f"🔍 `{ts}` 未找到表头，前30行：\n```\n" + "\n".join(lines[:30])[:1500] + "\n```")
        return

    # ===== 解析部分：简单直接，不猜结构 =====
    if not lines:
        send(f"⚠️ `{ts}` 页面无文字。")
        return

    start_idx = next((i for i, l in enumerate(lines) if "(比赛)" in l or "(Match)" in l), -1)
    if start_idx == -1:
        send(f"⚠️ `{ts}` 未找到 (比赛) 标识，前30行：\n```\n" + "\n".join(lines[:30])[:1500] + "\n```")
        return

    data = lines[start_idx:]
    parsed, i = [], 0

    while i < len(data):
        # 判断是否为一场比赛 (两行连续的 (比赛))
        if "(比赛)" in data[i] and i + 1 < len(data) and "(比赛)" in data[i + 1]:
            home = data[i].replace(" (比赛)", "").strip()
            away = data[i + 1].replace(" (比赛)", "").strip()
            i += 2
            m_time, odds = "未定时", []

            # 收集本场所有数字
            while i < len(data):
                nxt = data[i]
                if "(比赛)" in nxt: break
                if re.match(r'^\d{2}:\d{2}$', nxt): m_time = nxt
                elif re.match(r'^[+-]?\d+\.\d+$', nxt): odds.append(nxt)
                i += 1

            ml = [f"⚽ *{home} vs {away}* 🕒 `{m_time}`"]

            # 严格按照 3 / 4 / 4 的节奏切分，不想要的数字直接忽略
            # 1X2 (前3个)
            if len(odds) >= 3:
                ml.append(f"   🔹 `1X2` : {odds[0]} | {odds[1]} | {odds[2]}")

            # 亚盘 (第3~6个)
            if len(odds) >= 7:
                ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
            elif len(odds) >= 6:
                ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[5]}")

            # 大小球 (第7个之后)
            if len(odds) >= 11:
                ml.append(f"   🔹 `大小` : {odds[7]} | 大{odds[8]} | 小{odds[10]}")
            elif len(odds) >= 9:
                # 缺了部分，但还能凑出大小球
                ml.append(f"   🔹 `大小` : " + " | ".join(odds[7:]))

            if len(ml) > 1:
                parsed.append("\n".join(ml))
        else:
            i += 1

    if parsed:
        mid = max(1, len(parsed) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
    else:
        send(f"⚠️ `{ts}` 未解析出比赛，前30行：\n```\n" + "\n".join(data[:30])[:1500] + "\n```")


if __name__ == "__main__":
    main()

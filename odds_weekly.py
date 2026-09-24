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
    matches = []

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
            pg.goto("https://www.pinnacle.com/en/soccer/matchups",
                    timeout=60000, wait_until="domcontentloaded")
            time.sleep(8)
            pg.evaluate("""() => {
                const t = Array.from(document.querySelectorAll('button,div,span,a'))
                    .find(el => el.textContent.trim().toUpperCase() === 'LEAGUES');
                if (t) t.click();
            }""")
            time.sleep(5)
            pg.evaluate("""() => {
                const t = Array.from(document.querySelectorAll('a,div,span,li'))
                    .find(el => el.textContent.trim() === 'England - Premier League');
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

            # 🚨 核心改动：直接在页面里按“比赛卡片”抓取所有可见的赔率数字
            matches = pg.evaluate("""() => {
                const results = [];
                // 找所有包含 "(比赛)" 或 "(Match)" 的元素
                const teamNodes = Array.from(document.querySelectorAll('div,span'))
                    .filter(el => el.children.length === 0 &&
                                 (el.textContent.trim().endsWith('(比赛)') || el.textContent.trim().endsWith('(Match)')));

                // 每 2 个元素配对一场比赛
                for (let idx = 0; idx + 1 < teamNodes.length; idx += 2) {
                    const homeNode = teamNodes[idx];
                    const awayNode = teamNodes[idx + 1];
                    const home = homeNode.textContent.replace('(比赛)', '').replace('(Match)', '').trim();
                    const away = awayNode.textContent.replace('(比赛)', '').replace('(Match)', '').trim();

                    // 向上找到这整场比赛的外层容器
                    let container = homeNode.parentElement;
                    for (let k = 0; k < 5; k++) {
                        if (container && container.parentElement) container = container.parentElement;
                        if (container && container.querySelectorAll('button, div[class*="odd"]').length > 5) break;
                    }

                    // 从容器里抓所有看起来像赔率的数字
                    const odds = [];
                    const oddsNodes = container.querySelectorAll('button, div[class*="odd"], span[class*="odd"], div[role="button"]');
                    oddsNodes.forEach(n => {
                        const txt = n.textContent.trim();
                        if (/^[+-]?\\d+\\.\\d+$/.test(txt) && !odds.includes(txt)) {
                            odds.push(txt);
                        }
                    });

                    if (odds.length >= 3) {
                        results.push({home, away, odds});
                    }
                }
                return results;
            }""")

            # 如果抓到的比赛数据太少，说明卡片定位失败，退回纯文本
            if len(matches) < 3:
                text_dump = pg.evaluate("() => document.body ? document.body.innerText : ''")
                lines = [l.strip() for l in text_dump.split("\n") if l.strip()]
                matches = {"fallback": lines}

        except Exception as e:
            send(f"❌ `{ts}` 抓取异常: {str(e)[:200]}")
        finally:
            b.close()

    # 调试信息：看看抓到的是结构还是纯文本
    if isinstance(matches, dict) and "fallback" in matches:
        preview = "\n".join(matches["fallback"][:60])
        send(f"🔍 `{ts}` 退回纯文本前60行：\n```\n{preview[:1800]}\n```")
    elif isinstance(matches, list) and matches:
        # 发前 3 场的原始数据给你看
    debug_lines = []
        for m in matches[:3]:
            debug_lines.append(f"{m['home']} vs {m['away']}: {m['odds'][:12]}")
        send(f"🔍 `{ts}` 前3场原始赔率数据：\n```\n" + "\n".join(debug_lines)[:1500] + "\n```")
    else:
        send(f"⚠️ `{ts}` 未抓到任何比赛数据。")
    # ===== 解析部分 =====
    final_messages = []

    # 如果是结构化数据（列表）
    if isinstance(matches, list):
        for m in matches:
            home, away, odds = m['home'], m['away'], m['odds']
            total = len(odds)
            ml = [f"⚽ *{home} vs {away}*"]
            if total >= 3:
                ml.append(f"   🔹 `1X2` : {odds[0]} | {odds[1]} | {odds[2]}")
            if total >= 7:
                ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
            if total >= 11:
                ml.append(f"   🔹 `大小` : {odds[7]} | 大{odds[8]} | 小{odds[10]}")
            if len(ml) > 1:
                final_messages.append("\n".join(ml))
    # 如果是纯文本回退（字典）
    elif isinstance(matches, dict) and "fallback" in matches:
        data = matches["fallback"]
        i = 0
        while i < len(data):
            if ("(比赛)" in data[i] or "(Match)" in data[i]) and i + 1 < len(data):
                home = data[i].replace(" (比赛)", "").replace(" (Match)", "").strip()
                away = data[i + 1].replace(" (比赛)", "").replace(" (Match)", "").strip()
                i += 2
                odds = []
                while i < len(data):
                    if "(比赛)" in data[i] or "(Match)" in data[i]: break
                    if re.match(r'^[+-]?\d+\.\d+$', data[i]): odds.append(data[i])
                    i += 1
                ml = [f"⚽ *{home} vs {away}*"]
                if len(odds) >= 3:
                    ml.append(f"   🔹 `1X2` : {odds[0]} | {odds[1]} | {odds[2]}")
                if len(odds) >= 7:
                    ml.append(f"   🔹 `亚盘` : 主{odds[3]} | 主{odds[4]} | 客 {odds[6]}")
                if len(odds) >= 11:
                    ml.append(f"   🔹 `大小` : {odds[7]} | 大{odds[8]} | 小{odds[10]}")
                if len(ml) > 1:
                    final_messages.append("\n".join(ml))
            else:
                i += 1

    if final_messages:
        mid = max(1, len(final_messages) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(final_messages[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(final_messages[mid:]))
    else:
        send(f"⚠️ `{ts}` 未解析出比赛。")

if __name__ == "__main__":
    main()

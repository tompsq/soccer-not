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

    # 从表头位置开始，往下收集所有数字
    def collect_numbers(start_line, end_line):
        nums = []
        for j in range(start_line, min(end_line, len(lines))):
            val = lines[j].strip()
            if re.match(r'^[+-]?\d+\.\d+$', val):
                nums.append(val)
        return nums

    # 表头结束后的“比赛数据区”才是我们要的
    data_start = max(header_1x2, header_handicap, header_ou) + 1
    data_lines = lines[data_start:]

    # 找到每场比赛的起始行（含“(比赛)”或“(Match)”）
    match_indices = [j for j, l in enumerate(data_lines) if "(比赛)" in l or "(Match)" in l]

    # 两两配对
    pairs = []
    for j in range(0, len(match_indices) - 1, 2):
        pairs.append((match_indices[j], match_indices[j + 1]))

    parsed = []
    for idx, (h, a) in enumerate(pairs):
        home = data_lines[h].replace(" (比赛)", "").replace(" (Match)", "").strip()
        away = data_lines[a].replace(" (比赛)", "").replace(" (Match)", "").strip()
        
        # 该场比赛的数据范围：从客队行到下一场主队行
        seg_end = pairs[idx + 1][0] if idx + 1 < len(pairs) else len(data_lines)
        seg = data_lines[a:seg_end]

        # 在段内提取时间
        m_time = "未定时"
        for l in seg:
            if re.match(r'^\d{2}:\d{2}$', l.strip()):
                m_time = l.strip()
                break

        # 🚨 核心：从表头开始提取对应的三组数字
        # 1X2 数字：只取 1X2 表头到 HANDICAP 表头之间的数字
        n1x2 = collect_numbers(header_1x2, header_handicap)
        # 亚盘数字：只取 HANDICAP 到 OVER/UNDER 之间的数字
        n_handicap = collect_numbers(header_handicap, header_ou)
        # 大小球数字：只取 OVER/UNDER 之后的数字
        n_ou = collect_numbers(header_ou, len(lines))

        # 每次消费完，从对应的列表里去掉已经用掉的
        # 因为每场只出现一次，所以我们直接用“切片”的方式匹配到对应位置
        # 但因为每场数据是连续的，无法简单索引。
        # 我们改个策略：不做全局提取，而是在本场比赛的 seg 内部提取。
        # (上面的 collect_numbers 是全局的，会重复计算，所以这里我们用本地提取)
        
        seg_1x2, seg_hcp, seg_ou = [], [], []
        for l in seg:
            if re.match(r'^[+-]?\d+\.\d+$', l):
                seg_1x2.append(l.strip())

        total = len(seg_1x2)
        ml = [f"⚽ *{home} vs {away}* 🕒 `{m_time}`"]

        # 根据截图真实结构：3(1X2) + 4(亚盘) + 4(大小)
        if total >= 3:
            ml.append(f"   🔹 `1X2` : {seg_1x2[0]} | {seg_1x2[1]} | {seg_1x2[2]}")

        if total >= 7:
            # 亚盘取接下来的 4 个
            ml.append(f"   🔹 `亚盘` : 主{seg_1x2[3]} | 主{seg_1x2[4]} | 客 {seg_1x2[6]}")

        if total >= 11:
            # 大小球取剩下的 4 个
            ml.append(f"   🔹 `大小` : {seg_1x2[7]} | 大{seg_1x2[8]} | 小{seg_1x2[10]}")
        elif total > 7:
            # 如果不够 11 个，说明大小球缺盘口或只有赔率
            ml.append(f"   🔹 `大小` : " + " | ".join(seg_1x2[7:]))

        if len(ml) > 1:
            parsed.append("\n".join(ml))

    if parsed:
        mid = max(1, len(parsed) // 2)
        send(f"🎯 *【Pinnacle 英超盘口 (上)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[:mid]))
        send(f"🎯 *【Pinnacle 英超盘口 (下)】*\n🕒 `{ts}`\n\n" + "\n\n".join(parsed[mid:]))
    else:
        send(f"⚠️ `{ts}` 未解析出配对，前30行：\n```\n" + "\n".join(data_lines[:30])[:1500] + "\n```")


if __name__ == "__main__":
    main()

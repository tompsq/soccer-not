import pandas as pd
import math
import re
import unicodedata

MATCH_FILE = "matches.xlsx"
XG_FILE = "xg.xlsx"
OUTPUT = "results.xlsx"
XG_SHEETS = ["英超","西甲","意甲","德甲","法甲","葡超","比甲","苏超","英冠"]
EV_RECOMMEND = 0.05
EV_WATCH = 0.0

def poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def norm(name):
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKD", name).encode("ascii","ignore").decode()
    s = s.lower()
    s = re.sub(r"[\s\.\-_&']", "", s)
    for suffix in ["fc","cf","sc","afc","united","city","town","club"]:
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    return s

def load_xg():
    xg_map = {}
    league_avg = {}
    for sheet in XG_SHEETS:
        try:
            df = pd.read_excel(XG_FILE, sheet_name=sheet)
        except Exception as e:
            print(f"[跳过] sheet {sheet}: {e}")
            continue
        latest_season = None
        teams = []
        for _, row in df.iterrows():
            season = row.get("Season")
            team = row.get("Team")
            if pd.isna(season) or pd.isna(team):
                continue
            if latest_season is None:
                latest_season = season
            if season != latest_season:
                break
            xg = row.get("xG")
            xga = row.get("xGA")
            if pd.isna(xg) or pd.isna(xga):
                continue
            xg_map[(sheet, norm(team))] = {"xG": float(xg), "xGA": float(xga), "team": team}
            teams.append((float(xg), float(xga)))
        if teams:
            avg_xg = sum(t[0] for t in teams) / len(teams)
            avg_xga = sum(t[1] for t in teams) / len(teams)
            league_avg[sheet] = {"avg_xg": avg_xg, "avg_xga": avg_xga, "avg_goals": (avg_xg + avg_xga) / 2}
    return xg_map, league_avg

def find_xg(xg_map, league, team):
    n = norm(team)
    if (league, n) in xg_map:
        return xg_map[(league, n)]
    for (lg, k), v in xg_map.items():
        if lg != league:
            continue
        if n and (n in k or k in n) and abs(len(n)-len(k)) <= 6:
            return v
    return None

def calc_ev(row, xg_h, xg_a, league, league_avg):
    avg = league_avg.get(league)
    if not avg:
        return None
    avg_goals = avg["avg_goals"]
    home_attack = xg_h["xG"] / avg["avg_xg"]
    home_defense = xg_h["xGA"] / avg["avg_xga"]
    away_attack = xg_a["xG"] / avg["avg_xg"]
    away_defense = xg_a["xGA"] / avg["avg_xga"]
    lam_h = home_attack * away_defense * avg_goals
    lam_a = away_attack * home_defense * avg_goals

    max_g = 10
    p_home = p_draw = p_away = p_over = 0.0
    p_ah_win = p_ah_half = p_ah_lose = 0.0
    try:
        ah_line = float(row.get("临_亚盘"))
    except:
        ah_line = 0
    try:
        ou_line = float(row.get("临_大小"))
    except:
        ou_line = 0
    for i in range(max_g+1):
        for j in range(max_g+1):
            p = poisson(i, lam_h) * poisson(j, lam_a)
            if i > j: p_home += p
            if i == j: p_draw += p
            if i < j: p_away += p
            if i + j > ou_line: p_over += p
            diff = i - j
            if ah_line < 0:
                need = -ah_line
                if diff > need: p_ah_win += p
                elif abs(diff - need) < 1e-9: p_ah_half += p
                else: p_ah_lose += p
    p_under = 1 - p_over
    def ev(prob, odds):
        try:
            return prob * float(odds) - 1
        except:
            return None
    res = {
        "主胜EV": ev(p_home, row.get("临_主胜")),
        "平局EV": ev(p_draw, row.get("临_平局")),
        "客胜EV": ev(p_away, row.get("临_客胜")),
        "主让EV": None,
        "客受让EV": None,
        "大球EV": ev(p_over, row.get("临_大球")),
        "小球EV": ev(p_under, row.get("临_小球")),
    }
    try:
        hw = float(row.get("临_亚盘主"))
        aw = float(row.get("临_亚盘客"))
        res["主让EV"] = p_ah_win * hw + p_ah_half * (hw+1)/2 - 1
        res["客受让EV"] = p_ah_lose * aw + p_ah_half * (aw+1)/2 - 1
    except:
        pass
    return res


def main():
    print("读取 xG 表...")
    xg_map, league_avg = load_xg()
    print(f"  加载 {len(xg_map)} 支球队，{len(league_avg)} 个联赛均值")
    print("读取比赛表...")
    df = pd.read_excel(MATCH_FILE, sheet_name=0)
    results = []
    skipped = []
    for _, row in df.iterrows():
        league = str(row.get("联赛","")).strip()
        home = str(row.get("主队","")).strip()
        away = str(row.get("客队","")).strip()
        if not league or not home or not away or league == "nan":
            continue
        xg_h = find_xg(xg_map, league, home)
        xg_a = find_xg(xg_map, league, away)
        if not xg_h or not xg_a:
            skipped.append(f"{league} | {home} vs {away} | 主{'Y' if xg_h else 'N'} 客{'Y' if xg_a else 'N'}")
            continue
        evs = calc_ev(row, xg_h, xg_a, league, league_avg)
        if not evs:
            skipped.append(f"{league} | {home} vs {away} | 无联赛均值")
            continue
        rec = {
            "联赛": league, "主队": home, "客队": away,
            "主xG": round(xg_h["xG"],3), "客xG": round(xg_a["xG"],3),
            "主xGA": round(xg_h["xGA"],3), "客xGA": round(xg_a["xGA"],3),
        }
        rec.update({k: (round(v,4) if isinstance(v,float) else v) for k,v in evs.items()})
        recs = [k for k,v in evs.items() if isinstance(v,float) and v > EV_RECOMMEND]
        rec["推荐"] = ", ".join(recs) if recs else ""
        results.append(rec)
    out = pd.DataFrame(results)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\n计算完成：{len(results)} 场成功，{len(skipped)} 场跳过")
    print(f"结果已存 {OUTPUT}\n")
    if skipped:
        print("跳过场次：")
        for s in skipped:
            print(" ", s)
    if results:
        print("\n=== EV > 5% 推荐 ===")
        recs = [r for r in results if r["推荐"]]
        for r in recs:
            print(f"{r['联赛']} {r['主队']} vs {r['客队']} → {r['推荐']}")
        if not recs:
            print("无")

if __name__ == "__main__":
    main()

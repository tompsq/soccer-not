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
DIVERGENCE_LIMIT = 0.15

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
        seasons_order = []
        season_teams = {}
        for _, row in df.iterrows():
            season = row.get("Season")
            team = row.get("Team")
            if pd.isna(season) or pd.isna(team):
                continue
            xg = row.get("xG")
            xga = row.get("xGA")
            if pd.isna(xg) or pd.isna(xga):
                continue
            try:
                xg = float(xg)
                xga = float(xga)
            except (ValueError, TypeError):
                continue
            season = str(season)
            if season not in season_teams:
                season_teams[season] = []
                seasons_order.append(season)
            season_teams[season].append({
                "team": team, "norm": norm(team),
                "xG": xg, "xGA": xga
            })
        weights = [0.5, 0.3, 0.2]
        recent = seasons_order[:3]
        team_weighted = {}
        for w, s in zip(weights, recent):
            for t in season_teams[s]:
                key = (sheet, t["norm"])
                if key not in team_weighted:
                    team_weighted[key] = {"xG": 0.0, "xGA": 0.0, "team": t["team"], "wsum": 0.0}
                team_weighted[key]["xG"] += w * t["xG"]
                team_weighted[key]["xGA"] += w * t["xGA"]
                team_weighted[key]["wsum"] += w
        for key, v in team_weighted.items():
            if v["wsum"] > 0:
                v["xG"] /= v["wsum"]
                v["xGA"] /= v["wsum"]
                xg_map[key] = v
        if team_weighted:
            avg_xg = sum(v["xG"] for v in team_weighted.values()) / len(team_weighted)
            avg_xga = sum(v["xGA"] for v in team_weighted.values()) / len(team_weighted)
            league_avg[sheet] = {"avg_xg": avg_xg, "avg_xga": avg_xga, "avg_goals": (avg_xg + avg_xga)/2}
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
    print(f"[{league}] {row.get('主队')} vs {row.get('客队')} | lam_h={lam_h:.2f} lam_a={lam_a:.2f}")

    max_g = 10
    p_home = p_draw = p_away = p_over = 0.0
    p_ah_win = p_ah_half = p_ah_lose = 0.0

    # 解析让球盘口
    try:
        ah_line = float(row.get("临_亚盘"))
    except:
        ah_line = None
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
            if ah_line is not None and ah_line < 0:
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

    def mkt(odds):
        try:
            return 1 / float(odds)
        except:
            return None

    def ok(prob, odds):
        mp = mkt(odds)
        if mp is None or prob is None:
            return True
        return abs(prob - mp) < DIVERGENCE_LIMIT

    res = {}
    for name, prob, odds_key in [
        ("主胜EV", p_home, "临_主胜"),
        ("平局EV", p_draw, "临_平局"),
        ("客胜EV", p_away, "临_客胜"),
    ]:
        if ok(prob, row.get(odds_key)):
            res[name] = ev(prob, row.get(odds_key))
        else:
            res[name] = None
            print(f"  [分歧过滤] {name} 模型{prob:.2%} vs 市场{mkt(row.get(odds_key)):.2%}")

    # 让球 EV：只有 ah_line 有效且不为 0 时才算
    res["主让EV"] = None
    res["客受让EV"] = None
    if ah_line is not None and ah_line != 0:
        try:
            hw = float(row.get("临_亚盘主"))
            aw = float(row.get("临_亚盘客"))
            res["主让EV"] = p_ah_win * hw + p_ah_half * (hw+1)/2 - 1
            res["客受让EV"] = p_ah_lose * aw + p_ah_half * (aw+1)/2 - 1
        except Exception as e:
            print(f"  [让球异常] {e}")
    else:
        print(f"  [让球跳过] ah_line={ah_line}")

    # 大小球
    res["大球EV"] = ev(p_over, row.get("临_大球")) if ok(p_over, row.get("临_大球")) else None
    res["小球EV"] = ev(p_under, row.get("临_小球")) if ok(p_under, row.get("临_小球")) else None

    return res

    
def main():
    print("读取 xG 表...")
    xg_map, league_avg = load_xg()
    print(f"  加载 {len(xg_map)} 支球队，{len(league_avg)} 个联赛均值")
    for lg, v in league_avg.items():
        print(f"    {lg}: avg_xg={v['avg_xg']:.2f}, avg_xga={v['avg_xga']:.2f}")
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
    out.to_excel(OUTPUT, index=False)
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

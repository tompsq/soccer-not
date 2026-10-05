def sofascore_get(url):
    try:
        r = requests.get(url, headers=SH, timeout=12)
        if r.status_code == 200:
            return r.json()
        print(f"Sofascore {r.status_code}: {url[:80]}")
    except Exception as e:
        print(f"Sofascore 错误: {e}")
    return None

def try_sofascore_enrich(rows):
    print("开始尝试从 Sofascore 获取长期 xG 数据...")
    cache = {}  # 避免同一支球队重复请求

    for i, row in enumerate(rows):
        home = row.get("主队", "")
        away = row.get("客队", "")
        print(f"[{i+1}/{len(rows)}] 处理 {home} vs {away}")

        for side, team in [("主队xG", home), ("客队xG", away)]:
            if not team:
                continue
            if team in cache:
                row[side] = cache[team]
                continue

            try:
                # 1. 搜索球队
                search_url = f"https://api.sofascore.com/api/v1/search/all?q={requests.utils.quote(team)}"
                data = sofascore_get(search_url)
                team_id = None
                if data and "results" in data:
                    for item in data["results"]:
                        if item.get("type") == "team":
                            entity = item.get("entity", {})
                            name = entity.get("name", "")
                            if team.lower() in name.lower() or name.lower() in team.lower():
                                team_id = entity.get("id")
                                break
                    if not team_id:
                        # 退而求其次
                        for item in data["results"]:
                            if item.get("type") == "team":
                                team_id = item.get("entity", {}).get("id")
                                break

                if not team_id:
                    cache[team] = None
                    continue

                # 2. 尝试获取球队统计（接口可能变化，做多重保护）
                # 常见接口示例（实际可能需要调整）
                stats_url = f"https://api.sofascore.com/api/v1/team/{team_id}/unique-tournament/17/season/61627/statistics/overall"
                # 注意：上面的 unique-tournament 和 season ID 是示例，不同联赛不同
                # 为了通用性，这里先尝试通用接口，失败就跳过
                stats = sofascore_get(f"https://api.sofascore.com/api/v1/team/{team_id}/statistics/seasons")
                
                xg_value = None
                if stats:
                    # 这里只是结构示例，实际字段需要根据返回内容调整
                    # 暂时先标记已尝试
                    pass

                cache[team] = xg_value
                row[side] = xg_value
                time.sleep(1.0)  # 降低频率

            except Exception as e:
                print(f"  {team} 失败: {e}")
                cache[team] = None
                continue

    print("Sofascore 处理结束")
    return rows


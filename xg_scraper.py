import requests
import pandas as pd
import time
from datetime import datetime

BASE_URL = "https://www.sofascore.com/api/v1"

LEAGUES = {
    "Premier League": 17,
    "La Liga": 8,
    "Bundesliga": 35,
    "Serie A": 23,
    "Ligue 1": 34,
    "Championship": 18,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_json(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_current_season(tournament_id):
    url = f"{BASE_URL}/unique-tournament/{tournament_id}/seasons"

    data = get_json(url)

    seasons = data.get("seasons", [])

    if not seasons:
        raise Exception(
            f"No season found for tournament {tournament_id}"
        )

    # SofaScore normally returns newest season first
    return seasons[0]

def get_all_events(tournament_id, season_id):
    events = []

    page = 0

    while True:

        url = (
            f"{BASE_URL}/unique-tournament/"
            f"{tournament_id}/season/"
            f"{season_id}/events/last/{page}"
        )

        try:
            data = get_json(url)
        except requests.HTTPError:
            break

        page_events = data.get("events", [])

        if not page_events:
            break

        events.extend(page_events)

        if not data.get("hasNextPage", False):
            break

        page += 1

        time.sleep(0.3)

    return events

def get_match_xg(event_id):

    url = f"{BASE_URL}/event/{event_id}/statistics"

    try:
        data = get_json(url)
    except Exception:
        return None, None

    statistics = data.get("statistics", [])

    if not statistics:
        return None, None

    full_match = None

    for period in statistics:

        if period.get("period") == "ALL":
            full_match = period
            break

    if full_match is None:
        return None, None

    home_xg = None
    away_xg = None

    for group in full_match.get("groups", []):

        for item in group.get("statisticsItems", []):

            if item.get("key") == "expectedGoals":

                home_xg = item.get("homeValue")
                away_xg = item.get("awayValue")

                if home_xg is None:
                    home_xg = item.get("home")

                if away_xg is None:
                    away_xg = item.get("away")

                break

    return home_xg, away_xg

def main():

    rows = []

    print("Starting SofaScore xG scraper...")

    for league_name, tournament_id in LEAGUES.items():

        print()
        print("=" * 50)
        print(league_name)
        print("=" * 50)

        season = get_current_season(tournament_id)

        season_id = season["id"]
        season_name = season["name"]

        print(
            f"Season: {season_name} "
            f"(ID: {season_id})"
        )

        events = get_all_events(
            tournament_id,
            season_id
        )

        print(
            f"Events found: {len(events)}"
        )

        teams = {}

        for event in events:

            # Only completed matches
            status = event.get("status", {})

            if status.get("type") != "finished":
                continue

            home_team = event.get("homeTeam", {})
            away_team = event.get("awayTeam", {})

            home_id = home_team.get("id")
            away_id = away_team.get("id")

            if not home_id or not away_id:
                continue

            if home_id not in teams:
    teams[home_id] = {
        "League": league_name,
        "Team": home_team.get("name"),
        "Matches": 0,
        "xG": 0.0,
        "xGA": 0.0
    }

if away_id not in teams:
    teams[away_id] = {
        "League": league_name,
        "Team": away_team.get("name"),
        "Matches": 0,
        "xG": 0.0,
        "xGA": 0.0
    }

            if away_id not in teams:
                teams[away_id] = {
                    "League": league_name,
                    "Team": away_team.get("name"),
                    "Matches": 0,
                    "xG": 0.0,
                    "xGA": 0.0
                }

            home_xg, away_xg = get_match_xg(
                event["id"]
            )

            if home_xg is None or away_xg is None:
                print(
                    f"⚠️ Missing xG: "
                    f"{home_team.get('name')} vs "
                    f"{away_team.get('name')}"
                )
                continue

            try:
                home_xg = float(home_xg)
                away_xg = float(away_xg)
            except (ValueError, TypeError):
                continue

            teams[home_id]["Matches"] += 1
            teams[home_id]["xG"] += home_xg
            teams[home_id]["xGA"] += away_xg

            teams[away_id]["Matches"] += 1
            teams[away_id]["xG"] += away_xg
            teams[away_id]["xGA"] += home_xg

            time.sleep(0.15)

        for team in teams.values():

            matches = team["Matches"]

            team["xG"] =
          round(team["xG"], 2)
            team["xGA"] = round(team["xGA"], 2)

            if matches > 0:
                team["xG per Match"] = round(
                    team["xG"] / matches,
                    2
                )

                team["xGA per Match"] = round(
                    team["xGA"] / matches,
                    2
                )
            else:
                team["xG per Match"] = None
                team["xGA per Match"] = None

            team["Season"] = season_name

            rows.append(team)

    df = pd.DataFrame(rows)

    if df.empty:
        raise Exception(
            "No xG data collected."
        )

    df = df[
        [
            "League",
            "Season",
            "Team",
            "Matches",
            "xG",
            "xGA",
            "xG per Match",
            "xGA per Match"
        ]
    ]

    df = df.sort_values(
        ["League", "xG"],
        ascending=[True, False]
    )

    output_file = "sofascore_xg.xlsx"

    with pd.ExcelWriter(
        output_file,
        engine="openpyxl"
      ) as writer:

        df.to_excel(
            writer,
            sheet_name="Season xG",
            index=False
        )

    print()
    print("=" * 50)
    print("DONE")
    print("=" * 50)
    print(
        f"Teams: {len(df)}"
    )
    print(
        f"Output: {output_file}"
    )


if __name__ == "__main__":
    main()

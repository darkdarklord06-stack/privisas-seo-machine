import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from data_sources.modules.google_search_console import GoogleSearchConsole


ROOT = Path(__file__).resolve().parents[1]

WATCHWORDS_FILE = ROOT / "data" / "seo" / "watchwords.json"
RANK_HISTORY_FILE = ROOT / "data" / "seo" / "rank-history.json"
IMPROVEMENT_LOG_FILE = ROOT / "data" / "seo" / "improvement-log.json"

GSC_DELAY_DAYS = 3
MEASUREMENT_DAYS = 28


def load_json(path: Path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")


def normalize_keyword(value: str) -> str:
    return " ".join(value.lower().strip().split())


def priority_value(priority: str) -> int:
    values = {
        "high": 3,
        "medium": 2,
        "low": 1
    }

    return values.get(str(priority).lower(), 0)


def fetch_gsc_queries(
    gsc: GoogleSearchConsole,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "rowLimit": 25000
    }

    response = (
        gsc.service
        .searchanalytics()
        .query(
            siteUrl=gsc.site_url,
            body=request
        )
        .execute()
    )

    results = []

    for row in response.get("rows", []):
        results.append({
            "keyword": row["keys"][0],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": round(row.get("position", 0), 2)
        })

    return results


def previous_measurement(
    history: List[Dict[str, Any]],
    keyword: str
) -> Optional[Dict[str, Any]]:

    normalized = normalize_keyword(keyword)

    matches = [
        row
        for row in history
        if normalize_keyword(row.get("keyword", "")) == normalized
    ]

    if not matches:
        return None

    return matches[-1]


def was_previously_improved(
    improvement_log: List[Dict[str, Any]],
    keyword: str
) -> bool:

    normalized = normalize_keyword(keyword)

    for item in improvement_log:
        if normalize_keyword(item.get("keyword", "")) == normalized:
            return True

    return False


def build_measurements(
    watchwords: List[Dict[str, Any]],
    query_lookup: Dict[str, Dict[str, Any]],
    history: List[Dict[str, Any]],
    measurement_date: str,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:

    new_rows = []

    for watchword in watchwords:
        keyword = watchword["keyword"]
        normalized = normalize_keyword(keyword)

        gsc_row = query_lookup.get(normalized)

        previous = previous_measurement(history, keyword)

        if gsc_row:
            position = gsc_row["position"]
            impressions = gsc_row["impressions"]
            clicks = gsc_row["clicks"]
            ctr = round(gsc_row["ctr"] * 100, 2)
        else:
            position = None
            impressions = 0
            clicks = 0
            ctr = 0

        position_change = None

        if (
            previous
            and previous.get("position") is not None
            and position is not None
        ):
            position_change = round(
                previous["position"] - position,
                2
            )

        new_rows.append({
            "measurementDate": measurement_date,
            "periodStart": start_date,
            "periodEnd": end_date,
            "periodDays": MEASUREMENT_DAYS,
            "source": "google_search_console",
            "keyword": keyword,
            "targetPath": watchword.get("targetPath"),
            "status": watchword.get("status", "active"),
            "position": position,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "positionChange": position_change
        })

    return new_rows


def select_keyword(
    watchwords: List[Dict[str, Any]],
    query_lookup: Dict[str, Dict[str, Any]],
    improvement_log: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:

    candidates = []

    tracked_keywords = {
        normalize_keyword(item["keyword"])
        for item in watchwords
    }

    for watchword in watchwords:
        if watchword.get("status", "active") != "active":
            continue

        keyword = watchword["keyword"]
        normalized = normalize_keyword(keyword)
        data = query_lookup.get(normalized)

        position = data["position"] if data else None
        impressions = data["impressions"] if data else 0
        clicks = data["clicks"] if data else 0

        candidate = {
            "keyword": keyword,
            "targetPath": watchword.get("targetPath"),
            "priority": watchword.get("priority", "medium"),
            "position": position,
            "impressions": impressions,
            "clicks": clicks,
            "tracked": True
        }

        # 1. Position 2–10 with impressions.
        if (
            position is not None
            and 2 <= position <= 10
            and impressions > 0
        ):
            candidate["selectionTier"] = 1
            candidate["reason"] = (
                "Position 2–10 with impressions; closest opportunity to #1."
            )

            candidate["sortKey"] = (
                1,
                position,
                -impressions
            )

            candidates.append(candidate)
            continue

        # 2. Position 11–20 with impressions.
        if (
            position is not None
            and 11 <= position <= 20
            and impressions > 0
        ):
            candidate["selectionTier"] = 2
            candidate["reason"] = (
                "Position 11–20 with measurable impressions."
            )

            candidate["sortKey"] = (
                2,
                -impressions,
                position
            )

            candidates.append(candidate)
            continue

        # 3. Previously improved keyword that is active again.
        if was_previously_improved(improvement_log, keyword):
            candidate["selectionTier"] = 3
            candidate["reason"] = (
                "Previously improved keyword is active again and has not achieved #1."
            )

            candidate["sortKey"] = (
                3,
                position if position is not None else 999,
                -impressions
            )

            candidates.append(candidate)
            continue

        # 4. High-priority keyword without usable GSC rank.
        if (
            watchword.get("priority") == "high"
            and position is None
        ):
            candidate["selectionTier"] = 4
            candidate["reason"] = (
                "High-priority tracked keyword without usable GSC rank."
            )

            candidate["sortKey"] = (
                4,
                -priority_value(watchword.get("priority", "")),
                0
            )

            candidates.append(candidate)

    # 5. Promising untracked GSC query.
    for normalized, data in query_lookup.items():
        if normalized in tracked_keywords:
            continue

        position = data.get("position")
        impressions = data.get("impressions", 0)

        if (
            position is not None
            and 2 <= position <= 20
            and impressions > 0
        ):
            candidates.append({
                "keyword": data["keyword"],
                "targetPath": None,
                "priority": "discovered",
                "position": position,
                "impressions": impressions,
                "clicks": data.get("clicks", 0),
                "tracked": False,
                "selectionTier": 5,
                "reason": (
                    "Promising untracked query discovered in Google Search Console."
                ),
                "sortKey": (
                    5,
                    position,
                    -impressions
                )
            })

    if not candidates:
        return None

    candidates.sort(key=lambda item: item["sortKey"])

    selected = candidates[0]
    selected.pop("sortKey", None)

    return selected


def report_position_changes(
    measurements: List[Dict[str, Any]]
) -> None:

    increases = []
    decreases = []

    for row in measurements:
        change = row.get("positionChange")

        if change is None:
            continue

        if change >= 2:
            increases.append(row)

        elif change <= -2:
            decreases.append(row)

    print("")
    print("MAJOR RANKING INCREASES")
    print("-----------------------")

    if not increases:
        print("None")

    for row in increases:
        print(
            f"{row['keyword']} | "
            f"+{row['positionChange']} positions | "
            f"current={row['position']}"
        )

    print("")
    print("MAJOR RANKING DECREASES")
    print("-----------------------")

    if not decreases:
        print("None")

    for row in decreases:
        print(
            f"{row['keyword']} | "
            f"{row['positionChange']} positions | "
            f"current={row['position']}"
        )


def main():
    today = date.today()

    end = today - timedelta(days=GSC_DELAY_DAYS)
    start = end - timedelta(days=MEASUREMENT_DAYS - 1)

    measurement_date = today.isoformat()
    start_date = start.isoformat()
    end_date = end.isoformat()

    watchwords = load_json(WATCHWORDS_FILE, [])
    history = load_json(RANK_HISTORY_FILE, [])
    improvement_log = load_json(IMPROVEMENT_LOG_FILE, [])

    if not watchwords:
        print("No watchwords configured.")
        return

    print("PRIVISAS SEO RANK WATCH")
    print("=======================")
    print(f"Measurement period: {start_date} -> {end_date}")
    print(f"Source: Google Search Console")
    print("")

    gsc = GoogleSearchConsole()

    query_rows = fetch_gsc_queries(
        gsc,
        start_date,
        end_date
    )

    query_lookup = {
        normalize_keyword(row["keyword"]): row
        for row in query_rows
    }

    measurements = build_measurements(
        watchwords,
        query_lookup,
        history,
        measurement_date,
        start_date,
        end_date
    )

    # APPEND ONLY.
    history.extend(measurements)
    save_json(RANK_HISTORY_FILE, history)

    print("WATCHED KEYWORDS")
    print("----------------")

    for row in measurements:
        print(
            f"{row['keyword']} | "
            f"position={row['position']} | "
            f"impressions={row['impressions']} | "
            f"clicks={row['clicks']} | "
            f"CTR={row['ctr']}%"
        )

    report_position_changes(measurements)

    selected = select_keyword(
        watchwords,
        query_lookup,
        improvement_log
    )

    print("")
    print("SELECTED KEYWORD")
    print("----------------")

    if not selected:
        print("No worthwhile optimization candidate found.")
        print("")
        print("No SEO change should be made today.")
        return

    print(f"Keyword: {selected['keyword']}")
    print(f"Target page: {selected.get('targetPath')}")
    print(f"Position: {selected.get('position')}")
    print(f"Impressions: {selected.get('impressions')}")
    print(f"Clicks: {selected.get('clicks')}")
    print(f"Selection tier: {selected.get('selectionTier')}")
    print(f"Reason: {selected.get('reason')}")

    print("")
    print("NEXT STEP")

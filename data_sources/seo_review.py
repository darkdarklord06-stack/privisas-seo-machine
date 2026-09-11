import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from data_sources.modules.google_search_console import GoogleSearchConsole


ROOT = Path(__file__).resolve().parents[1]

WATCHWORDS_FILE = ROOT / "data" / "seo" / "watchwords.json"
RANK_HISTORY_FILE = ROOT / "data" / "seo" / "rank-history.json"
IMPROVEMENT_LOG_FILE = ROOT / "data" / "seo" / "improvement-log.json"

SITE_BASE_URL = "https://privisas.com"

# Search Console standard data can lag a few days.
GSC_DELAY_DAYS = 3

# Experiment measurement period.
REVIEW_DAYS = 7


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


def parse_date(value: str) -> date:
    return datetime.strptime(
        value,
        "%Y-%m-%d"
    ).date()


def full_target_url(target_path: str) -> str:
    if target_path.startswith("http"):
        return target_path

    return SITE_BASE_URL.rstrip("/") + "/" + target_path.lstrip("/")


def fetch_query_page_metrics(
    gsc: GoogleSearchConsole,
    keyword: str,
    target_path: str,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:

    target_url = full_target_url(target_path)

    request = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensionFilterGroups": [
            {
                "filters": [
                    {
                        "dimension": "query",
                        "operator": "equals",
                        "expression": keyword
                    },
                    {
                        "dimension": "page",
                        "operator": "equals",
                        "expression": target_url
                    }
                ]
            }
        ],
        "rowLimit": 1
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

    rows = response.get("rows", [])

    if not rows:
        return {
            "position": None,
            "impressions": 0,
            "clicks": 0,
            "ctr": 0.0
        }

    row = rows[0]

    return {
        "position": round(
            row.get("position", 0),
            2
        ),
        "impressions": row.get(
            "impressions",
            0
        ),
        "clicks": row.get(
            "clicks",
            0
        ),
        "ctr": round(
            row.get("ctr", 0) * 100,
            2
        )
    }


def evaluate_result(
    before: Dict[str, Any],
    after: Dict[str, Any]
) -> Dict[str, Any]:

    before_position = before.get("position")
    after_position = after.get("position")

    if (
        after_position is not None
        and after_position <= 1.5
        and after.get("impressions", 0) >= 3
    ):
        return {
            "outcome": "achieved",
            "reason": (
                "Average position reached approximately #1 "
                "with measurable impressions."
            )
        }

    if (
        before_position is not None
        and after_position is not None
    ):
        position_change = round(
            before_position - after_position,
            2
        )

        if position_change >= 1.0:
            return {
                "outcome": "improved_but_not_achieved",
                "reason": (
                    f"Average position improved by "
                    f"{position_change} positions."
                )
            }

        if position_change <= -1.5:
            return {
                "outcome": "negative",
                "reason": (
                    f"Average position declined by "
                    f"{abs(position_change)} positions."
                )
            }

    if (
        after.get("clicks", 0) > before.get("clicks", 0)
        and after.get("impressions", 0) > 0
    ):
        return {
            "outcome": "improved_but_not_achieved",
            "reason": (
                "Clicks increased during the post-change period."
            )
        }

    return {
        "outcome": "no_effect",
        "reason": (
            "No sufficiently strong positive or negative "
            "change was measured in the 7-day comparison."
        )
    }


def find_watchword(
    watchwords,
    keyword: str
) -> Optional[Dict[str, Any]]:

    for item in watchwords:
        if item.get("keyword") == keyword:
            return item

    return None


def main():
    today = date.today()

    # Latest date we consider safely available in normal GSC data.
    available_through = (
        today - timedelta(days=GSC_DELAY_DAYS)
    )

    watchwords = load_json(
        WATCHWORDS_FILE,
        []
    )

    history = load_json(
        RANK_HISTORY_FILE,
        []
    )

    improvement_log = load_json(
        IMPROVEMENT_LOG_FILE,
        []
    )

    due_experiments = []

    for experiment in improvement_log:
        if experiment.get("status") != "observing":
            continue

        next_review = experiment.get(
            "nextReviewDate"
        )

        if not next_review:
            continue

        if parse_date(next_review) <= today:
            due_experiments.append(
                experiment
            )

    print("PRIVISAS SEO EXPERIMENT REVIEW")
    print("==============================")
    print(f"Today: {today.isoformat()}")
    print(
        f"GSC safely available through: "
        f"{available_through.isoformat()}"
    )
    print("")

    if not due_experiments:
        print(
            "No SEO experiments are due for review today."
        )
        return

    gsc = GoogleSearchConsole()

    changes_made = False

    for experiment in due_experiments:
        keyword = experiment["keyword"]
        target_path = experiment["targetPath"]

        action_date = parse_date(
            experiment["actionDate"]
        )

        # Seven complete days BEFORE the change.
        before_end = (
            action_date - timedelta(days=1)
        )
        before_start = (
            before_end - timedelta(
                days=REVIEW_DAYS - 1
            )
        )

        # Seven complete days AFTER the change.
        after_start = (
            action_date + timedelta(days=1)
        )
        after_end = (
            after_start + timedelta(
                days=REVIEW_DAYS - 1
            )
        )

        print(f"Keyword: {keyword}")
        print(
            f"Target: "
            f"{full_target_url(target_path)}"
        )
        print(
            f"Action date: "
            f"{action_date.isoformat()}"
        )
        print(
            f"Required post-change period: "
            f"{after_start.isoformat()} -> "
            f"{after_end.isoformat()}"
        )

        # Do not evaluate incomplete post-change data.
        if after_end > available_through:
            ready_date = (
                after_end
                + timedelta(
                    days=GSC_DELAY_DAYS
                )
            )

            print(
                "⏳ Review deferred: complete "
                "7-day post-change GSC data "
                "is not available yet."
            )
            print(
                f"Earliest safe evaluation date: "
                f"{ready_date.isoformat()}"
            )
            print("")
            continue

        before = fetch_query_page_metrics(
            gsc,
            keyword,
            target_path,
            before_start,
            before_end
        )

        after = fetch_query_page_metrics(
            gsc,
            keyword,
            target_path,
            after_start,
            after_end
        )

        result = evaluate_result(
            before,
            after
        )

        position_change = None

        if (
            before.get("position") is not None
            and after.get("position") is not None
        ):
            position_change = round(
                before["position"]
                - after["position"],
                2
            )

        experiment["status"] = (
            result["outcome"]
        )

        experiment["evaluation"] = {
            "evaluatedDate": today.isoformat(),

            "beforePeriod": {
                "start": before_start.isoformat(),
                "end": before_end.isoformat(),
                **before
            },

            "afterPeriod": {
                "start": after_start.isoformat(),
                "end": after_end.isoformat(),
                **after
            },

            "positionChange": position_change,
            "outcome": result["outcome"],
            "reason": result["reason"]
        }

        watchword = find_watchword(
            watchwords,
            keyword
        )

        if watchword:
            if result["outcome"] == "achieved":
                watchword["status"] = "achieved"
            else:
                watchword["status"] = "active"

            watchword.pop(
                "nextReviewDate",
                None
            )

        # rank-history is APPEND ONLY.
        history.append({
            "measurementDate": today.isoformat(),
            "source": "google_search_console",
            "measurementType": "experiment_review_7_day",
            "keyword": keyword,
            "targetPath": target_path,

            "beforePeriod": {
                "start": before_start.isoformat(),
                "end": before_end.isoformat()
            },

            "afterPeriod": {
                "start": after_start.isoformat(),
                "end": after_end.isoformat()
            },

            "beforePosition": before.get(
                "position"
            ),
            "afterPosition": after.get(
                "position"
            ),
            "positionChange": position_change,

            "beforeImpressions": before.get(
                "impressions",
                0
            ),
            "afterImpressions": after.get(
                "impressions",
                0
            ),

            "beforeClicks": before.get(
                "clicks",
                0
            ),
            "afterClicks": after.get(
                "clicks",
                0
            ),

            "beforeCtr": before.get(
                "ctr",
                0
            ),
            "afterCtr": after.get(
                "ctr",
                0
            ),

            "evaluationResult": (
                result["outcome"]
            )
        })

        print("")
        print("BEFORE")
        print("------")
        print(
            f"Position: {before['position']}"
        )
        print(
            f"Impressions: "
            f"{before['impressions']}"
        )
        print(
            f"Clicks: {before['clicks']}"
        )
        print(
            f"CTR: {before['ctr']}%"
        )

        print("")
        print("AFTER")
        print("-----")
        print(
            f"Position: {after['position']}"
        )
        print(
            f"Impressions: "
            f"{after['impressions']}"
        )
        print(
            f"Clicks: {after['clicks']}"
        )
        print(
            f"CTR: {after['ctr']}%"
        )

        print("")
        print(
            f"RESULT: "
            f"{result['outcome']}"
        )
        print(
            f"Reason: "
            f"{result['reason']}"
        )
        print("")

        changes_made = True

    if changes_made:
        save_json(
            WATCHWORDS_FILE,
            watchwords
        )

        save_json(
            IMPROVEMENT_LOG_FILE,
            improvement_log
        )

        save_json(
            RANK_HISTORY_FILE,
            history
        )

        print(
            "✅ SEO experiment review data saved."
        )
    else:
        print(
            "No experiment was evaluated yet."
        )


if __name__ == "__main__":
    main()

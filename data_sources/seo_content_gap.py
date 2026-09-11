import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from data_sources.modules.google_search_console import GoogleSearchConsole
from data_sources.seo_rank_watch import (
    fetch_gsc_queries,
    load_json,
    normalize_keyword,
    select_keyword,
)


ROOT = Path(__file__).resolve().parents[1]

WATCHWORDS_FILE = ROOT / "data" / "seo" / "watchwords.json"
IMPROVEMENT_LOG_FILE = ROOT / "data" / "seo" / "improvement-log.json"
CONTENT_GAP_TASK_FILE = ROOT / "data" / "seo" / "content-gap-task.json"

SITE_BASE_URL = "https://privisas.com"

GSC_DELAY_DAYS = 3
MEASUREMENT_DAYS = 28


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )
        f.write("\n")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def determine_search_intent(keyword: str) -> Dict[str, str]:
    query = normalize_keyword(keyword)

    if any(term in query for term in [
        "yeterli mi",
        "gerekli mi",
        "olur mu",
        "kabul edilir mi"
    ]):
        return {
            "type": "informational_decision",
            "searcher": (
                "Vize başvurusu hazırlayan ve belirli bir belgenin "
                "başvuru için yeterli olup olmadığını kontrol eden kullanıcı."
            ),
            "goal": (
                "Belgenin tek başına yeterli olup olmadığını ve gerekiyorsa "
                "hangi ek belgelerin hazırlanması gerektiğini öğrenmek."
            )
        }

    if any(term in query for term in [
        "nasıl",
        "başvuru",
        "randevu",
        "nereden"
    ]):
        return {
            "type": "procedural",
            "searcher": (
                "Vize sürecinde bir işlemi nasıl yapacağını öğrenmek isteyen kullanıcı."
            ),
            "goal": (
                "Doğru başvuru adımlarını ve yapılması gereken işlemleri öğrenmek."
            )
        }

    if any(term in query for term in [
        "nedir",
        "ne demek",
        "neden"
    ]):
        return {
            "type": "informational",
            "searcher": (
                "Bir vize kavramı veya gerekliliği hakkında bilgi arayan kullanıcı."
            ),
            "goal": (
                "Konuyu hızlı, açık ve doğru biçimde anlamak."
            )
        }

    if any(term in query for term in [
        "ücret",
        "fiyat",
        "kaç tl",
        "maliyet"
    ]):
        return {
            "type": "commercial_information",
            "searcher": (
                "Vize sürecinin maliyetini araştıran kullanıcı."
            ),
            "goal": (
                "Güncel ücretleri ve toplam başvuru maliyetini öğrenmek."
            )
        }

    return {
        "type": "informational",
        "searcher": (
            "Vize veya seyahat süreci hakkında bilgi arayan kullanıcı."
        ),
        "goal": (
            "Aradığı konu hakkında doğru ve uygulanabilir bilgi edinmek."
        )
    }


def fetch_target_page(target_path: str) -> Dict[str, Any]:
    url = urljoin(SITE_BASE_URL, target_path)

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; PrivisasSEOAgent/1.0; "
                "+https://privisas.com)"
            )
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = clean_text(
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    description = ""

    meta_description = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta_description:
        description = clean_text(
            meta_description.get("content", "")
        )

    headings: List[Dict[str, str]] = []

    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = clean_text(
            heading.get_text(" ", strip=True)
        )

        if text:
            headings.append({
                "level": heading.name,
                "text": text
            })

    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        tag.decompose()

    body_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    if len(body_text) > 20000:
        body_text = body_text[:20000]

    return {
        "url": url,
        "title": title,
        "metaDescription": description,
        "headings": headings,
        "bodyText": body_text
    }


def main():
    today = date.today()

    end = today - timedelta(days=GSC_DELAY_DAYS)
    start = end - timedelta(days=MEASUREMENT_DAYS - 1)

    watchwords = load_json(
        WATCHWORDS_FILE,
        []
    )

    improvement_log = load_json(
        IMPROVEMENT_LOG_FILE,
        []
    )

    gsc = GoogleSearchConsole()

    query_rows = fetch_gsc_queries(
        gsc,
        start.isoformat(),
        end.isoformat()
    )

    query_lookup = {
        normalize_keyword(row["keyword"]): row
        for row in query_rows
    }

    selected = select_keyword(
        watchwords,
        query_lookup,
        improvement_log
    )

    print("PRIVISAS SEO CONTENT GAP")
    print("========================")

    if not selected:
        print("No optimization candidate found.")
        return

    keyword = selected["keyword"]
    target_path = selected.get("targetPath")

    if not target_path:
        print(
            "Selected query has no confirmed target page. "
            "Human review required before optimization."
        )
        return

    intent = determine_search_intent(keyword)
    target_page = fetch_target_page(target_path)

    task = {
        "createdDate": today.isoformat(),
        "status": "prepared_for_serp_research",

        "keyword": keyword,
        "targetPath": target_path,

        "gsc": {
            "position": selected.get("position"),
            "impressions": selected.get("impressions"),
            "clicks": selected.get("clicks"),
            "selectionTier": selected.get(
                "selectionTier"
            ),
            "selectionReason": selected.get(
                "reason"
            )
        },

        "searchIntent": intent,

        "targetPage": target_page,

        "serpResearch": {
            "required": True,
            "results": [],
            "note": (
                "Google SERP must be researched through an approved "
                "search provider or web-search agent. "
                "Do not scrape Google search result pages directly."
            )
        },

        "contentGap": {
            "status": "not_analyzed",
            "missingInformation": [],
            "hypothesis": None
        },

        "publishing": {
            "allowed": False,
            "note": (
                "No Framer change may be published until SERP and "
                "content-gap analysis is complete."
            )
        }
    }

    save_json(
        CONTENT_GAP_TASK_FILE,
        task
    )

    print(f"Keyword: {keyword}")
    print(
        f"Position: "
        f"{selected.get('position')}"
    )
    print(
        f"Impressions: "
        f"{selected.get('impressions')}"
    )
    print(
        f"Target: "
        f"{target_page['url']}"
    )

    print("")
    print("SEARCH INTENT")
    print("-------------")
    print(
        f"Type: {intent['type']}"
    )
    print(
        f"Searcher: {intent['searcher']}"
    )
    print(
        f"Goal: {intent['goal']}"
    )

    print("")
    print("TARGET PAGE")
    print("-----------")
    print(
        f"Title: {target_page['title']}"
    )

    print(
        f"Headings found: "
        f"{len(target_page['headings'])}"
    )

    print("")
    print(
        "✅ Content-gap research task created:"
    )
    print(
        "data/seo/content-gap-task.json"
    )

    print("")
    print(
        "Next: inspect the current top organic "
        "results and compare them with this page."
    )


if __name__ == "__main__":
    main()

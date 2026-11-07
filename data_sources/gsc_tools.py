"""Privisas GSC tools: sitemap submit, URL inspection, page performance.
Run in GitHub Actions (Workload Identity). Read-only except sitemap submit."""
import os, sys, json, datetime
import google.auth
from googleapiclient.discovery import build

SITE = os.getenv("GSC_SITE_URL", "sc-domain:privisas.com")
ACTION = os.getenv("GSC_ACTION", "inspect")
URLS = [u.strip() for u in os.getenv("GSC_URLS", "").split(",") if u.strip()]
scope = "https://www.googleapis.com/auth/webmasters" + ("" if ACTION == "sitemap" else ".readonly")
creds, _ = google.auth.default(scopes=[scope])
svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
out = {"action": ACTION, "site": SITE, "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "results": []}

if ACTION == "sitemap":
    feed = URLS[0] if URLS else "https://privisas.com/sitemap.xml"
    svc.sitemaps().submit(siteUrl=SITE, feedpath=feed).execute()
    sm = svc.sitemaps().get(siteUrl=SITE, feedpath=feed).execute()
    out["results"].append({"feed": feed, "lastSubmitted": sm.get("lastSubmitted"), "lastDownloaded": sm.get("lastDownloaded"), "isPending": sm.get("isPending"), "warnings": sm.get("warnings"), "errors": sm.get("errors")})
elif ACTION == "inspect":
    for u in URLS:
        try:
            r = svc.urlInspection().index().inspect(body={"inspectionUrl": u, "siteUrl": SITE, "languageCode": "tr-TR"}).execute()
            ix = r.get("inspectionResult", {}).get("indexStatusResult", {})
            out["results"].append({"url": u, "verdict": ix.get("verdict"), "coverage": ix.get("coverageState"), "lastCrawl": ix.get("lastCrawlTime"), "googleCanonical": ix.get("googleCanonical"), "fetch": ix.get("pageFetchState"), "robots": ix.get("robotsTxtState")})
        except Exception as e:
            out["results"].append({"url": u, "error": str(e)[:300]})
elif ACTION == "performance":
    end = datetime.date.today() - datetime.timedelta(days=2); start = end - datetime.timedelta(days=27)
    body = {"startDate": str(start), "endDate": str(end), "dimensions": ["page"], "rowLimit": 100}
    rows = svc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
    out["period"] = [str(start), str(end)]
    out["results"] = [{"page": r["keys"][0], "clicks": r["clicks"], "impressions": r["impressions"], "ctr": round(r["ctr"], 4), "position": round(r["position"], 1)} for r in rows]
elif ACTION == "queries":
    end = datetime.date.today() - datetime.timedelta(days=2); start = end - datetime.timedelta(days=27)
    body = {"startDate": str(start), "endDate": str(end), "dimensions": ["query", "page"], "rowLimit": 250}
    rows = svc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
    out["period"] = [str(start), str(end)]
    out["results"] = [{"query": r["keys"][0], "page": r["keys"][1].replace("https://privisas.com", ""), "clicks": r["clicks"], "impressions": r["impressions"], "ctr": round(r["ctr"], 4), "position": round(r["position"], 1)} for r in rows]
else:
    sys.exit(f"unknown action {ACTION}")

os.makedirs("output", exist_ok=True)
with open("output/gsc-tools-result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))

import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

OPEN_PATH = Path("data/open-jobs.json")
APPLIED_PATH = Path("data/applied-jobs.json")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"jobs": []}


def extract_jobs(value):
    found = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("title") and item.get("company"):
                found.append(item)
            else:
                found.extend(extract_jobs(item))
    elif isinstance(value, dict):
        if value.get("title") and value.get("company"):
            found.append(value)
        else:
            for child in value.values():
                if isinstance(child, (list, dict)):
                    found.extend(extract_jobs(child))
    return found


def norm(value):
    value = str(value or "").lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def allowed_title(title):
    t = str(title or "").strip()
    # Only Data Scientist / Lead Data Scientist. Descriptive suffixes are allowed
    # only when separated by punctuation, e.g. "Data Scientist - Pricing".
    return bool(re.match(
        r"^(?:Lead\s+Data\s+Scientist|Data\s+Scientist)(?:\s*(?:[-–—:,(\/]|$).*)?$",
        t,
        flags=re.IGNORECASE,
    ))


def canonical_url(url):
    if not url:
        return ""
    try:
        parts = urlsplit(str(url).strip())
        host = parts.netloc.lower().replace("www.", "")
        path = re.sub(r"/+$", "", parts.path)
        # LinkedIn tracking query params change every fetch, so ignore queries/fragments.
        return urlunsplit((parts.scheme.lower() or "https", host, path, "", ""))
    except Exception:
        return str(url).strip().split("?", 1)[0].split("#", 1)[0].rstrip("/")


def linkedin_job_id(job):
    raw_id = str(job.get("id") or "")
    m = re.search(r"(?:linkedin:)?(\d{7,})", raw_id)
    if m:
        return m.group(1)
    for field in ("url", "portalUrl", "aggUrl", "jdUrl"):
        m = re.search(r"-(\d{7,})(?:\?|$|/)", str(job.get(field) or ""))
        if m:
            return m.group(1)
    return ""


def identity_sets(job):
    ids, urls, signatures = set(), set(), set()
    jid = linkedin_job_id(job)
    if jid:
        ids.add(jid)
    for field in ("url", "portalUrl", "aggUrl", "jdUrl", "jobUrl", "applyUrl"):
        u = canonical_url(job.get(field))
        if u:
            urls.add(u)
    title = norm(job.get("title"))
    company = norm(job.get("company"))
    location = norm(job.get("location"))
    if title and company:
        signatures.add((title, company, location))
        signatures.add((title, company, ""))
    return ids, urls, signatures


def build_seen(jobs):
    ids, urls, signatures = set(), set(), set()
    for job in jobs:
        ji, ju, js = identity_sets(job)
        ids |= ji
        urls |= ju
        signatures |= js
    return ids, urls, signatures


def is_seen(job, seen):
    ids, urls, signatures = identity_sets(job)
    seen_ids, seen_urls, seen_signatures = seen
    return bool(ids & seen_ids or urls & seen_urls or signatures & seen_signatures)


def add_seen(job, seen):
    ids, urls, signatures = identity_sets(job)
    seen[0].update(ids)
    seen[1].update(urls)
    seen[2].update(signatures)


def main():
    open_data = load_json(OPEN_PATH)
    applied_data = load_json(APPLIED_PATH)

    open_jobs = extract_jobs(open_data)
    applied_jobs = extract_jobs(applied_data)
    applied_seen = build_seen(applied_jobs)
    kept_seen = (set(), set(), set())
    kept = []

    for job in open_jobs:
        if not allowed_title(job.get("title")):
            continue
        if is_seen(job, applied_seen):
            continue
        if is_seen(job, kept_seen):
            continue
        kept.append(job)
        add_seen(job, kept_seen)

    if isinstance(open_data, dict):
        open_data["jobs"] = kept
        open_data["filterPolicy"] = "Data Scientist + Lead Data Scientist only; excludes Jobs Applied and duplicate Open Roles"
        output = open_data
    else:
        output = kept

    OPEN_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Open Roles sanitized: {len(open_jobs)} -> {len(kept)}")


if __name__ == "__main__":
    main()

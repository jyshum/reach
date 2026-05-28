"""Resolve founder email addresses from multiple sources.

Cascade: website scrape → pattern guess + SMTP verify.
Runs offline on dev machine. Only attempts founders with has_email=True.
"""

import json
import os
import re
import smtplib
import socket
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FOUNDERS_PATH = os.path.join(_ROOT, "data", "founders.json")
RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw_companies.json")
OUTPUT_PATH = os.path.join(_ROOT, "data", "resolved_emails.json")

REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 10
LOG_EVERY = 25

GENERIC_PREFIXES = {
    "info", "hello", "hi", "contact", "support", "help", "team",
    "admin", "sales", "press", "media", "jobs", "careers", "hr",
    "billing", "legal", "privacy", "security", "noreply", "no-reply",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

WEBSITE_PATHS = ["", "/contact", "/about", "/team", "/about-us", "/contact-us"]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def extract_domain(url: str | None) -> str | None:
    """Extract the root domain from a URL (strip www, path, etc)."""
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        if len(parts) > 2:
            host = ".".join(parts[-2:])
        return host if host else None
    except Exception:
        return None


def extract_emails_from_html(html: str, domain: str) -> list[str]:
    """Extract all email addresses matching a domain from HTML content."""
    all_emails = EMAIL_REGEX.findall(html.lower())
    return list(set(e for e in all_emails if e.endswith(f"@{domain}")))


def filter_generic_emails(emails: list[str]) -> list[str]:
    """Remove generic addresses (info@, support@, etc)."""
    return [e for e in emails if e.split("@")[0] not in GENERIC_PREFIXES]


def guess_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """Generate candidate email addresses from name + domain."""
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    if not first or not domain:
        return []
    patterns = [
        f"{first}@{domain}",
        f"{first}.{last}@{domain}",
        f"{first}{last}@{domain}",
    ]
    if last:
        patterns.append(f"{first[0]}.{last}@{domain}")
    return patterns


def match_founder_email(
    emails: list[str], first_name: str, last_name: str
) -> str | None:
    """Pick the email most likely belonging to the founder."""
    if not emails:
        return None
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    for email in emails:
        local = email.split("@")[0]
        if first in local:
            return email
    for email in emails:
        local = email.split("@")[0]
        if last and last in local:
            return email
    return emails[0]


def fetch_page(url: str) -> str | None:
    """Fetch a web page, return HTML or None on failure."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        return resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, socket.timeout, Exception):
        return None


def scrape_website_for_email(
    website: str, domain: str, founder_first: str, founder_last: str
) -> str | None:
    """Crawl a company website for the founder's email address."""
    base = website.rstrip("/")
    all_emails = []

    for path in WEBSITE_PATHS:
        url = base + path
        html = fetch_page(url)
        if html:
            found = extract_emails_from_html(html, domain)
            all_emails.extend(found)
        time.sleep(0.5)

    personal = filter_generic_emails(all_emails)
    if personal:
        return match_founder_email(personal, founder_first, founder_last)
    return None


def check_mx_records(domain: str) -> bool:
    """Check if domain has MX records (accepts email)."""
    import subprocess
    try:
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def verify_smtp(email: str, domain: str) -> bool:
    """Attempt SMTP verification of an email address."""
    import subprocess
    try:
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            capture_output=True, text=True, timeout=5,
        )
        mx_lines = result.stdout.strip().split("\n")
        if not mx_lines or not mx_lines[0]:
            return False
        mx_host = mx_lines[0].split()[-1].rstrip(".")

        server = smtplib.SMTP(timeout=5)
        server.connect(mx_host, 25)
        server.helo("reach-verify.local")
        server.mail("verify@reach-verify.local")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False


def split_founder_name(full_name: str) -> tuple[str, str]:
    """Split 'First Last' into (first, last). Handles edge cases."""
    if not full_name:
        return ("", "")
    parts = full_name.strip().split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    return (first, last)


def resolve_all_emails(
    founders_path: str = FOUNDERS_PATH,
    raw_path: str = RAW_DATA_PATH,
    output_path: str = OUTPUT_PATH,
):
    """Run the full email resolution cascade."""
    with open(founders_path) as f:
        founders = json.load(f)
    with open(raw_path) as f:
        raw = json.load(f)

    website_map = {c["name"]: c.get("website", "") for c in raw}

    # Load existing results for resume support
    existing = {}
    if os.path.exists(output_path):
        with open(output_path) as f:
            for entry in json.load(f):
                existing[entry["company_name"]] = entry

    results = list(existing.values())
    resolved_names = set(existing.keys())

    stats = {"website": 0, "pattern": 0, "failed": 0}

    eligible = [f for f in founders if f.get("has_email") and f["company_name"] not in resolved_names]
    print(f"[INFO] {len(eligible)} founders to resolve ({len(resolved_names)} already done)")

    for i, founder in enumerate(eligible):
        name = founder["company_name"]
        founder_name = founder.get("founder_name") or ""
        website = website_map.get(name, "")
        domain = extract_domain(website)
        first, last = split_founder_name(founder_name)

        resolved_email = None
        source = None
        confidence = None

        # Step 1: Website scrape
        if domain and website:
            resolved_email = scrape_website_for_email(website, domain, first, last)
            if resolved_email:
                source = "website"
                confidence = "high"
                stats["website"] += 1

        # Step 2: Pattern guess + MX/SMTP verify
        if not resolved_email and domain and first:
            candidates = guess_email_patterns(first, last, domain)
            if check_mx_records(domain):
                for candidate in candidates:
                    if verify_smtp(candidate, domain):
                        resolved_email = candidate
                        source = "pattern"
                        confidence = "medium"
                        stats["pattern"] += 1
                        break

        if not resolved_email:
            stats["failed"] += 1

        results.append({
            "company_name": name,
            "founder_email": resolved_email,
            "email_source": source,
            "email_confidence": confidence,
        })

        done = i + 1
        if done % LOG_EVERY == 0 or done == len(eligible):
            print(f"[INFO] {done}/{len(eligible)} processed | website={stats['website']} pattern={stats['pattern']} failed={stats['failed']}")

        if done % LOG_EVERY == 0:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)

        time.sleep(REQUEST_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    total_resolved = stats["website"] + stats["pattern"]
    print(f"[DONE] Resolved {total_resolved}/{len(eligible)} emails")
    print(f"  Website: {stats['website']}")
    print(f"  Pattern+SMTP: {stats['pattern']}")
    print(f"  Failed: {stats['failed']}")
    return results


if __name__ == "__main__":
    resolve_all_emails()

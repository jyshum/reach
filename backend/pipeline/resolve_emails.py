"""Resolve founder email addresses from multiple sources.

Cascade: website scrape → GitHub discovery → pattern guess + MX verify.
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

PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com",
    "live.com", "yahoo.com", "yahoo.co.uk", "icloud.com", "me.com",
    "mac.com", "aol.com", "protonmail.com", "proton.me", "pm.me",
    "fastmail.com", "zoho.com", "mail.com", "gmx.com", "gmx.net",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

WEBSITE_PATHS = ["", "/contact", "/about", "/team", "/about-us", "/contact-us"]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# GitHub API — unauthenticated rate limit is 60 req/hr, sufficient for targeted lookups
GITHUB_API = "https://api.github.com"


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


# ---------- GitHub discovery ----------


def _github_api_get(path: str) -> dict | list | None:
    """Hit the GitHub API. Returns parsed JSON or None."""
    try:
        req = Request(
            f"{GITHUB_API}{path}",
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _extract_github_username(url: str | None) -> str | None:
    """Extract a GitHub username from a URL like github.com/username."""
    if not url:
        return None
    match = re.search(r"github\.com/([a-zA-Z0-9_-]+)", url)
    if match:
        username = match.group(1)
        # Filter out org-level pages that aren't usernames
        if username.lower() not in {"orgs", "settings", "marketplace", "explore"}:
            return username
    return None


def _find_github_username(founder: dict, company_desc: str) -> str | None:
    """Try to find a GitHub username from founder/company data."""
    # Check founder bio for github.com links
    bio = founder.get("founder_bio") or ""
    username = _extract_github_username(bio)
    if username:
        return username

    # Check LinkedIn URL (some people use github links in LinkedIn)
    # Not useful directly, but the founder name can be tried as a username

    # Check company description for github org
    username = _extract_github_username(company_desc)
    if username:
        return username

    return None


def discover_email_from_github(
    founder_name: str, domain: str, founder: dict, company_desc: str
) -> str | None:
    """Try to find founder email via GitHub.

    Strategy:
    1. Find GitHub username from bio/description
    2. Check public email on their profile
    3. Scan their recent public commits for @company-domain emails
    """
    username = _find_github_username(founder, company_desc)
    if not username:
        return None

    # Check profile public email
    user_data = _github_api_get(f"/users/{username}")
    if not user_data:
        return None

    public_email = user_data.get("email")
    if public_email:
        email_lower = public_email.lower()
        email_domain = email_lower.split("@")[-1]
        # Accept company domain emails directly
        if domain and email_lower.endswith(f"@{domain}"):
            return public_email
        # Accept personal emails — it's on their profile, so it's theirs
        if email_domain in PERSONAL_EMAIL_DOMAINS:
            return public_email

    # Scan recent public events for commit emails
    events = _github_api_get(f"/users/{username}/events/public?per_page=30")
    if not events or not isinstance(events, list):
        return None

    first, last = split_founder_name(founder_name)
    found_emails = set()

    for event in events:
        if event.get("type") != "PushEvent":
            continue
        payload = event.get("payload", {})
        for commit in payload.get("commits", []):
            author = commit.get("author", {})
            email = (author.get("email") or "").lower()
            if not email or email.split("@")[0] in GENERIC_PREFIXES:
                continue
            email_domain = email.split("@")[-1]
            # Accept company domain emails
            if domain and email.endswith(f"@{domain}"):
                found_emails.add(email)
            # Accept personal emails only if founder name appears in local part
            elif email_domain in PERSONAL_EMAIL_DOMAINS:
                local = email.split("@")[0]
                if first and first.lower() in local:
                    found_emails.add(email)

    if found_emails:
        return match_founder_email(list(found_emails), first, last)

    return None


# ---------- MX / SMTP verification ----------


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
    desc_map = {
        c["name"]: (c.get("long_description") or "") + " " + (c.get("description") or "")
        for c in raw
    }

    # Load existing results for resume support
    existing = {}
    if os.path.exists(output_path):
        with open(output_path) as f:
            for entry in json.load(f):
                existing[entry["company_name"]] = entry

    results = list(existing.values())
    resolved_names = set(existing.keys())

    stats = {"website": 0, "github": 0, "pattern_smtp": 0, "pattern_mx": 0, "failed": 0}

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

        # Step 2: GitHub discovery
        if not resolved_email and domain:
            company_desc = desc_map.get(name, "")
            resolved_email = discover_email_from_github(
                founder_name, domain, founder, company_desc,
            )
            if resolved_email:
                source = "github"
                confidence = "high"
                stats["github"] += 1

        # Step 3: Pattern guess + verification
        if not resolved_email and domain and first:
            candidates = guess_email_patterns(first, last, domain)
            if check_mx_records(domain):
                # Try SMTP verification first
                smtp_verified = False
                for candidate in candidates:
                    if verify_smtp(candidate, domain):
                        resolved_email = candidate
                        source = "pattern"
                        confidence = "medium"
                        stats["pattern_smtp"] += 1
                        smtp_verified = True
                        break

                # If SMTP didn't work (server blocks probing), accept
                # first pattern with MX-valid domain as low confidence
                if not smtp_verified:
                    resolved_email = candidates[0]  # first@domain.com
                    source = "pattern"
                    confidence = "low"
                    stats["pattern_mx"] += 1

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
            total_resolved = stats["website"] + stats["github"] + stats["pattern_smtp"] + stats["pattern_mx"]
            print(
                f"[INFO] {done}/{len(eligible)} processed | "
                f"website={stats['website']} github={stats['github']} "
                f"pattern_smtp={stats['pattern_smtp']} pattern_mx={stats['pattern_mx']} "
                f"failed={stats['failed']} | total_resolved={total_resolved}"
            )

        if done % LOG_EVERY == 0:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)

        time.sleep(REQUEST_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    total_resolved = stats["website"] + stats["github"] + stats["pattern_smtp"] + stats["pattern_mx"]
    print(f"\n[DONE] Resolved {total_resolved}/{len(eligible)} emails")
    print(f"  Website scrape (high):     {stats['website']}")
    print(f"  GitHub discovery (high):   {stats['github']}")
    print(f"  Pattern + SMTP (medium):   {stats['pattern_smtp']}")
    print(f"  Pattern + MX only (low):   {stats['pattern_mx']}")
    print(f"  Failed (no domain/MX):     {stats['failed']}")
    return results


if __name__ == "__main__":
    resolve_all_emails()

#!/usr/bin/env python3
"""
Vision One — SPF/DKIM/DMARC Email Authentication Report

Queries Vision One XDR email activity logs and produces a detailed CSV report
for email admins to monitor and troubleshoot authentication failures.

Output CSV columns:
    timestamp, sender, sender_domain, sender_ip, recipient, subject,
    spf_result, dkim_result, dmarc_result, action, product, delivery_status,
    message_id

Also prints summary: counts by result, by domain, and by day.

Requirements:
    pip install requests

Usage:
    python v1_spf_query.py                          # 7 days, uses key from script
    python v1_spf_query.py --days 30                # 30 days
    python v1_spf_query.py --key YOUR_KEY --days 14 # override key

API Key Permissions Required:
    - Search > Email Activity Data (View)
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ============================================================
# CONFIGURATION — Paste your API key and region here
# ============================================================
V1_API_KEY = ""          # Paste your Vision One API key here
V1_REGION = "us"         # Options: us, eu, jp, sg, au, in
# ============================================================

REGIONS = {
    "us": "https://api.xdr.trendmicro.com",
    "eu": "https://api.eu.xdr.trendmicro.com",
    "jp": "https://api.xdr.trendmicro.co.jp",
    "sg": "https://api.sg.xdr.trendmicro.com",
    "au": "https://api.au.xdr.trendmicro.com",
    "in": "https://api.in.xdr.trendmicro.com",
}


def fetch_email_logs(base_url, api_key, start_dt, end_dt, top=200):
    """Page through all email activity logs in the time range."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json;charset=utf-8",
        "TMV1-Query": "*",
    }
    params = {
        "startDateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "top": top,
    }

    all_items = []
    url = f"{base_url}/v3.0/search/emailActivities"
    page = 0

    while url and page < 100:
        resp = requests.get(
            url,
            headers=headers,
            params=params if page == 0 else None,
            timeout=60,
        )

        if resp.status_code == 401:
            print("Error: Authentication failed. Check your API key.")
            sys.exit(1)
        elif resp.status_code == 403:
            print("Error: API key lacks permission for email activity search.")
            print("Required: Search > Email Activity Data (View)")
            sys.exit(1)
        elif resp.status_code != 200:
            print(f"Error: API returned {resp.status_code}")
            print(resp.text[:500])
            sys.exit(1)

        data = resp.json()
        items = data.get("items", [])
        all_items.extend(items)
        page += 1

        progress = data.get("progressRate", 100)
        sys.stderr.write(
            f"\r  Fetching... page {page}, {len(all_items)} records, {progress}% complete"
        )

        url = data.get("nextLink")
        if progress < 100 and not url:
            time.sleep(2)

    sys.stderr.write("\n")
    return all_items


def extract_domain(email_addr):
    """Extract domain from email address."""
    if not email_addr:
        return ""
    if "@" in email_addr:
        return email_addr.split("@")[-1].lower()
    return email_addr.lower()


def classify_passfail(result_str):
    """Classify an SPF/DKIM/DMARC result as pass or fail."""
    if not result_str:
        return ""
    return "pass" if result_str.lower() == "pass" else "fail"


def parse_record(item):
    """Extract all relevant fields from a single email activity record."""
    # Sender info
    suser = item.get("suser", [])
    sender = suser[0] if suser else ""
    sender_domain = extract_domain(sender)
    sender_ip = item.get("mailSenderIp", "")

    # Recipient
    duser = item.get("duser", [])
    smtp_rcpt = item.get("mailSmtpRecipients", [])
    recipient = duser[0] if duser else (smtp_rcpt[0] if smtp_rcpt else "")

    # Message details
    subject = item.get("mailMsgSubject", "")
    msg_id = item.get("mailMsgId", "")
    product = item.get("pname", item.get("productCode", ""))
    delivery = item.get("deliveryStatus", "")

    # Timestamp
    timestamp = item.get("eventTimeDT", "")
    if not timestamp:
        evt_ms = item.get("eventTime")
        if evt_ms:
            timestamp = datetime.fromtimestamp(evt_ms / 1000, tz=timezone.utc).isoformat()

    # SPF/DKIM/DMARC from scannerDetails (CEGP only)
    spf_result = ""
    spf_action = ""
    dkim_result = ""
    dkim_action = ""
    dmarc_spf = ""
    dmarc_dkim = ""
    dmarc_alignment = ""
    dmarc_action = ""

    # Skip non-CEGP records (CECP doesn't do domain auth)
    if item.get("productCode") != "sem":
        return None

    scanner = item.get("scannerDetails", {})
    for result in scanner.get("policyScanResults", []):
        name = result.get("name", "")
        auth = result.get("domainAuthResult", {})
        action = result.get("action", "")

        if name == "SPF Rule":
            spf_result = auth.get("spfResult", "")
            spf_action = action
        elif name == "DKIM Rule":
            dkim_result = auth.get("dkimResult", "")
            dkim_action = action
        elif name == "DMARC Rule":
            dmarc_spf = result.get("triggerReason", "")
            dmarc_action = action

    # Derive DMARC pass/fail: triggerReason present = fail
    dmarc_passfail = ""
    if dmarc_action:
        dmarc_passfail = "fail" if dmarc_spf else "pass"

    return {
        "timestamp": timestamp,
        "spf_passfail": classify_passfail(spf_result),
        "spf_detail": spf_result,
        "spf_action": spf_action,
        "dkim_action": dkim_action,
        "dmarc_passfail": dmarc_passfail,
        "dmarc_trigger": dmarc_spf,
        "dmarc_action": dmarc_action,
        "sender": sender,
        "sender_domain": sender_domain,
        "sender_ip": sender_ip,
        "recipient": recipient,
        "subject": subject,
        "product": product,
        "delivery_status": delivery,
        "message_id": msg_id,
    }


def write_csv(records, filepath):
    """Write records to CSV."""
    if not records:
        return
    fieldnames = [
        "timestamp",
        "spf_passfail", "spf_detail", "spf_action",
        "dkim_action",
        "dmarc_passfail", "dmarc_trigger", "dmarc_action",
        "sender", "sender_domain", "sender_ip", "recipient",
        "subject", "product", "delivery_status", "message_id",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def print_summary(records, total_raw):
    """Print summary tables: by result, by domain, by day."""
    records_with_spf = [r for r in records if r["spf_detail"]]

    print(f"\n{'=' * 60}")
    print(f"  Vision One — CEGP Email Authentication Report")
    print(f"{'=' * 60}")
    print(f"  CEGP records analyzed:         {total_raw}")
    print(f"  Records with SPF result:       {len(records_with_spf)}")
    print(f"{'=' * 60}")

    # --- SPF counts ---
    spf_counter = Counter(r["spf_detail"] for r in records_with_spf)
    print(f"\n  {'SPF Result':<15} {'Count':>8} {'Pct':>8}")
    print(f"  {'-'*15} {'-'*8} {'-'*8}")
    for val, cnt in spf_counter.most_common():
        pct = (cnt / len(records_with_spf)) * 100
        print(f"  {val:<15} {cnt:>8} {pct:>6.1f}%")

    # --- Failures by sender domain ---
    failure_types = {"softfail", "permerror", "temperror", "fail"}
    failures = [r for r in records_with_spf if r["spf_detail"].lower() in failure_types]
    if failures:
        print(f"\n  {'─' * 50}")
        print(f"  SPF FAILURES BY SENDER DOMAIN ({len(failures)} total)")
        print(f"  {'─' * 50}")
        domain_counter = Counter(r["sender_domain"] for r in failures)
        print(f"  {'Domain':<30} {'Count':>8} {'Results'}")
        print(f"  {'-'*30} {'-'*8} {'-'*20}")
        for domain, cnt in domain_counter.most_common(20):
            results = Counter(r["spf_detail"] for r in failures if r["sender_domain"] == domain)
            result_str = ", ".join(f"{k}:{v}" for k, v in results.most_common())
            print(f"  {domain:<30} {cnt:>8} {result_str}")

    # --- Counts by day ---
    print(f"\n  {'─' * 50}")
    print(f"  SPF RESULTS BY DAY")
    print(f"  {'─' * 50}")
    day_results = defaultdict(Counter)
    for r in records_with_spf:
        day = r["timestamp"][:10] if r["timestamp"] else "unknown"
        day_results[day][r["spf_detail"]] += 1

    print(f"  {'Date':<12} {'Total':>6} {'Pass':>6} {'SoftFail':>9} {'Fail':>6} {'PermErr':>8} {'TempErr':>8}")
    print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*9} {'-'*6} {'-'*8} {'-'*8}")
    for day in sorted(day_results.keys()):
        c = day_results[day]
        total = sum(c.values())
        print(f"  {day:<12} {total:>6} {c.get('pass',0):>6} {c.get('softfail',0):>9} {c.get('fail',0):>6} {c.get('permerror',0):>8} {c.get('temperror',0):>8}")

    # --- Counts by sender domain (top 15) ---
    print(f"\n  {'─' * 50}")
    print(f"  SPF RESULTS BY SENDER DOMAIN (top 15)")
    print(f"  {'─' * 50}")
    domain_all = defaultdict(Counter)
    for r in records_with_spf:
        domain_all[r["sender_domain"]][r["spf_detail"]] += 1

    sorted_domains = sorted(domain_all.items(), key=lambda x: sum(x[1].values()), reverse=True)[:15]
    print(f"  {'Domain':<30} {'Total':>6} {'Pass':>6} {'SoftFail':>9} {'Fail':>6} {'Other':>6}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*9} {'-'*6} {'-'*6}")
    for domain, c in sorted_domains:
        total = sum(c.values())
        other = total - c.get("pass", 0) - c.get("softfail", 0) - c.get("fail", 0)
        print(f"  {domain:<30} {total:>6} {c.get('pass',0):>6} {c.get('softfail',0):>9} {c.get('fail',0):>6} {other:>6}")

    # --- Top sender IPs for failures ---
    if failures:
        print(f"\n  {'─' * 50}")
        print(f"  TOP SENDER IPs FOR SPF FAILURES")
        print(f"  {'─' * 50}")
        ip_counter = Counter(r["sender_ip"] for r in failures if r["sender_ip"])
        print(f"  {'Sender IP':<20} {'Count':>8} {'Domains'}")
        print(f"  {'-'*20} {'-'*8} {'-'*30}")
        for ip, cnt in ip_counter.most_common(10):
            domains = set(r["sender_domain"] for r in failures if r["sender_ip"] == ip)
            print(f"  {ip:<20} {cnt:>8} {', '.join(sorted(domains)[:3])}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="SPF/DKIM/DMARC report from Vision One email activity logs"
    )
    parser.add_argument(
        "--key", default="",
        help="V1 API key (or paste into V1_API_KEY at top of script)",
    )
    parser.add_argument(
        "--region", default="",
        choices=[""] + list(REGIONS.keys()),
        help="V1 region (default: us)",
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Days to look back (default: 7)"
    )
    parser.add_argument(
        "--top", type=int, default=200, help="Results per page (default: 200)"
    )
    parser.add_argument(
        "--no-file", action="store_true", help="Don't write output files"
    )
    args = parser.parse_args()

    api_key = args.key or V1_API_KEY or os.environ.get("V1_API_KEY", "")
    region = args.region or V1_REGION or "us"

    if not api_key:
        print("Error: API key required.")
        print("  Option 1: Paste into V1_API_KEY at the top of this script")
        print("  Option 2: Use --key flag")
        print("  Option 3: Set V1_API_KEY environment variable")
        sys.exit(1)

    base_url = REGIONS[region]
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=args.days)

    print(f"Querying Vision One ({region.upper()}) email activity logs...")
    print(f"  Period: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} ({args.days} days)")

    items = fetch_email_logs(base_url, api_key, start_dt, end_dt, args.top)

    if not items:
        print("\nNo email activity records found in the specified time range.")
        sys.exit(0)

    records = [r for r in (parse_record(item) for item in items) if r is not None]
    print(f"  CEGP (gateway) records:  {len(records)} of {len(items)} total")
    if not records:
        print("\nNo CEGP records found. CECP (inline) records don't include domain auth data.")
        sys.exit(0)
    print_summary(records, len(records))

    if not args.no_file:
        skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir = os.path.join(skill_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(reports_dir, f"spf_report_{timestamp}.csv")
        write_csv(records, csv_path)
        print(f"CSV report saved to: {csv_path}")


if __name__ == "__main__":
    main()

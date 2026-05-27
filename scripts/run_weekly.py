from __future__ import annotations

import argparse

from _automation import (
    fetch_enabled_sources,
    generate_weekly_report,
    maybe_email_report,
    process_items,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fetch_enabled_sources(dry_run=args.dry_run or args.skip_fetch)
    process_items(update_seen=not args.dry_run)
    report = generate_weekly_report()
    print(f"Weekly report: {report}")
    maybe_email_report(report, no_email=args.no_email, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

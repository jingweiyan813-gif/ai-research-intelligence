from __future__ import annotations

import argparse

from _automation import (
    ecosystem_source_ids,
    fetch_enabled_sources,
    generate_ecosystem_report,
    maybe_email_report,
    process_items,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fetch_enabled_sources(
        dry_run=args.dry_run or args.skip_fetch,
        source_ids=ecosystem_source_ids(),
    )
    process_items(update_seen=False)
    report = generate_ecosystem_report()
    print(f"Ecosystem report: {report}")
    maybe_email_report(report, no_email=args.no_email, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse

from _automation import generate_alerts_report, maybe_email_report, process_items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    process_items(update_seen=False)
    report = generate_alerts_report()
    print(f"Alerts report: {report}")
    text = report.read_text(encoding="utf-8")
    no_alerts = "No high-signal alerts." in text
    maybe_email_report(
        report,
        no_email=args.no_email or no_alerts,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

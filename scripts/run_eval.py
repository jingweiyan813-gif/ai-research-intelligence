from __future__ import annotations

from _automation import render_eval_report


def main() -> None:
    report = render_eval_report()
    print(f"Eval report: {report}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import pytest

from airi.delivery import EmailConfigError, EmailDelivery, preview_without_credentials


def test_email_preview_writes_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = preview_without_credentials("Subject", "Body", tmp_path)

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Subject: Subject" in text
    assert "Body" in text


def test_missing_env_vars_fail_clearly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    for name in [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASS",
        "REPORT_FROM_EMAIL",
        "REPORT_TO_EMAIL",
    ]:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(EmailConfigError, match="Missing email environment variables"):
        EmailDelivery.from_env()


def test_email_send_does_not_print_secret(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):  # type: ignore[no-untyped-def]
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *args):  # type: ignore[no-untyped-def]
            return None

        def starttls(self):  # type: ignore[no-untyped-def]
            sent["tls"] = True

        def login(self, user, password):  # type: ignore[no-untyped-def]
            sent["user"] = user
            sent["password_seen"] = password == "super-secret"

        def send_message(self, message):  # type: ignore[no-untyped-def]
            sent["subject"] = message["Subject"]

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    delivery = EmailDelivery(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_pass="super-secret",
        from_email="from@example.com",
        to_email="to@example.com",
    )

    delivery.send("Subject", "Body")

    captured = capsys.readouterr()
    assert "super-secret" not in captured.out
    assert "super-secret" not in captured.err
    assert sent["password_seen"] is True


def test_invalid_email_format_fails() -> None:
    with pytest.raises(EmailConfigError, match="REPORT_FROM_EMAIL"):
        EmailDelivery(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_pass="pass",
            from_email="not-email",
            to_email="to@example.com",
        )


def test_email_preview_preserves_chinese_utf8(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = preview_without_credentials("[AI 技术情报] 周报", "中文正文", tmp_path)

    from email import policy
    from email.parser import Parser

    message = Parser(policy=policy.default).parsestr(path.read_text(encoding="utf-8"))
    assert message["Subject"] == "[AI 技术情报] 周报"
    assert message.get_content().strip() == "中文正文"

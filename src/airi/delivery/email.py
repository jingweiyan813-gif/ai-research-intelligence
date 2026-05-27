from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

_REQUIRED_ENV = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASS",
    "REPORT_FROM_EMAIL",
    "REPORT_TO_EMAIL",
)


class EmailConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailDelivery:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    from_email: str
    to_email: str
    use_tls: bool = True

    def __post_init__(self) -> None:
        if self.smtp_port <= 0:
            raise EmailConfigError("SMTP_PORT must be a positive integer")
        _validate_email(self.from_email, "REPORT_FROM_EMAIL")
        for email in _split_recipients(self.to_email):
            _validate_email(email, "REPORT_TO_EMAIL")

    @classmethod
    def from_env(cls) -> EmailDelivery:
        missing = [name for name in _REQUIRED_ENV if not os.getenv(name)]
        if missing:
            raise EmailConfigError(
                "Missing email environment variables: " + ", ".join(missing)
            )
        try:
            port = int(os.environ["SMTP_PORT"])
        except ValueError as exc:
            raise EmailConfigError("SMTP_PORT must be a positive integer") from exc
        use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() not in {
            "0",
            "false",
            "no",
        }
        return cls(
            smtp_host=os.environ["SMTP_HOST"],
            smtp_port=port,
            smtp_user=os.environ["SMTP_USER"],
            smtp_pass=os.environ["SMTP_PASS"],
            from_email=os.environ["REPORT_FROM_EMAIL"],
            to_email=os.environ["REPORT_TO_EMAIL"],
            use_tls=use_tls,
        )

    def send(self, subject: str, body: str) -> None:
        message = self._message(subject, body)
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
            if self.use_tls:
                smtp.starttls()
            smtp.login(self.smtp_user, self.smtp_pass)
            smtp.send_message(message)

    def preview(self, subject: str, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "email_preview.eml"
        path.write_text(self._message(subject, body).as_string(), encoding="utf-8")
        return path

    def _message(self, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = self.to_email
        message.set_content(body)
        return message


def preview_without_credentials(
    subject: str,
    body: str,
    output_dir: Path,
    *,
    from_email: str = "preview@example.com",
    to_email: str = "recipient@example.com",
) -> Path:
    delivery = EmailDelivery(
        smtp_host="preview.invalid",
        smtp_port=25,
        smtp_user="preview",
        smtp_pass="preview",
        from_email=from_email,
        to_email=to_email,
        use_tls=False,
    )
    return delivery.preview(subject, body, output_dir)


def _split_recipients(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _validate_email(value: str, env_name: str) -> None:
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise EmailConfigError(f"{env_name} must look like an email address")

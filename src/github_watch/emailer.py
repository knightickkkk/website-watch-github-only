from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable
import mimetypes
import os
import smtplib
import ssl


@dataclass(slots=True)
class EmailConfig:
    host: str
    port: int
    username: str
    password: str
    mail_from: str

    @classmethod
    def from_env(cls) -> "EmailConfig":
        missing = [
            key
            for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM")
            if not os.getenv(key)
        ]
        if missing:
            raise RuntimeError(f"Missing email env vars: {', '.join(missing)}")

        return cls(
            host=os.environ["SMTP_HOST"],
            port=int(os.environ["SMTP_PORT"]),
            username=os.environ["SMTP_USER"],
            password=os.environ["SMTP_PASSWORD"],
            mail_from=os.environ["MAIL_FROM"],
        )


def send_email(
    config: EmailConfig,
    *,
    to: str,
    subject: str,
    body: str,
    attachments: Iterable[Path] = (),
) -> None:
    message = EmailMessage()
    message["From"] = config.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    for attachment in attachments:
        _attach_file(message, attachment)

    context = ssl.create_default_context()
    if config.port == 465:
        with smtplib.SMTP_SSL(config.host, config.port, context=context) as smtp:
            smtp.login(config.username, config.password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(config.host, config.port) as smtp:
            smtp.starttls(context=context)
            smtp.login(config.username, config.password)
            smtp.send_message(message)


def _attach_file(message: EmailMessage, path: Path) -> None:
    content_type, _ = mimetypes.guess_type(path.name)
    if content_type:
        maintype, subtype = content_type.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"

    message.add_attachment(
        path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )

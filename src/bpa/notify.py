import smtplib
import ssl
from email.message import EmailMessage

from bpa.config import SmtpSettings
from bpa.pipeline import PipelineResult

SMTP_TIMEOUT_SECONDS = 15
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024 
XLSX_TYPE = ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class NotificationError(Exception):
    """Raised when the notification email cannot be built or sent."""


def build_message(result: PipelineResult, settings: SmtpSettings) -> EmailMessage:

    message = EmailMessage()
  
    message["Subject"] = (
        f"[BPA] {result.verdict} - {len(result.violations)} exception(s), "
        f"{len(result.rejected)} rejected line(s)"
    )
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)

    try:
        report_size = result.report_path.stat().st_size

        report_bytes = (
            result.report_path.read_bytes() if report_size <= MAX_ATTACHMENT_BYTES else None
        )
    except OSError as exc:
        raise NotificationError(f"Cannot read the report to attach it ({type(exc).__name__})") from exc

    lines = [
        f"Run ID: {result.run_id}",
        f"Result: {result.verdict}",
        f"Lines read: {result.lines_read} "
        f"(valid: {result.valid_count}, rejected: {len(result.rejected)})",
        f"Exceptions: {len(result.violations)} "
        f"(blocking: {result.blocking_count}, warnings: {result.warning_count})",
        "",
    ]
    if report_bytes is None:
        lines.append(
            f"The report is too large to attach. It is saved as "
            f"{result.report_path.name} on the machine that ran the tool."
        )
    else:
        lines.append("The full report is attached.")
    message.set_content("\n".join(lines))

    if report_bytes is not None:
        maintype, subtype = XLSX_TYPE
        
        message.add_attachment(
            report_bytes, maintype=maintype, subtype=subtype, filename=result.report_path.name
        )
    return message


def _deliver(server: smtplib.SMTP, message: EmailMessage, settings: SmtpSettings) -> None:
    if settings.username is not None and settings.password is not None:
        server.login(settings.username, settings.password)
    server.send_message(message)


def send_notification(message: EmailMessage, settings: SmtpSettings) -> None:
  
    context = ssl.create_default_context()
    try:
        if settings.security == "ssl":
         
            with smtplib.SMTP_SSL(
                settings.host, settings.port, timeout=SMTP_TIMEOUT_SECONDS, context=context
            ) as server:
                _deliver(server, message, settings)
        else:
            with smtplib.SMTP(settings.host, settings.port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if settings.security == "starttls":
                  
                    server.starttls(context=context)
                _deliver(server, message, settings)
    except (smtplib.SMTPException, OSError) as exc:

        raise NotificationError(f"Could not send the email ({type(exc).__name__}: {exc})") from exc
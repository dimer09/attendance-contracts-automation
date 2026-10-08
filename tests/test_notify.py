import smtplib
import ssl
from email.message import EmailMessage

import pytest

from bpa import notify
from bpa.config import SmtpSettings
from bpa.models import RuleViolation, Severity
from bpa.notify import NotificationError, build_message, send_notification
from bpa.pipeline import PipelineResult
from bpa.validate import RejectedRow
from tests.factories import make_record

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def make_settings(**overrides):
    base = {
        "host": "smtp.example.com",
        "port": 587,
        "security": "starttls",
        "sender": "bpa@example.com",
        "recipients": ("manager@example.com",),
        "username": "bpa-user",
        "password": "smtp-secret",
    }
    return SmtpSettings(**{**base, **overrides})


def make_violation(rule_code="R1", severity=Severity.BLOCKING, **record_overrides):
    return RuleViolation(
        rule_code, severity, make_record(**record_overrides), f"{rule_code} problem"
    )


def make_rejected():
    raw = {"employee_id": "M001", "name": "Mbuyi", "client": "Acme", "date": "x", "hours": "8"}
    return RejectedRow(3, raw, "date: bad")


def make_result(tmp_path, *, violations=(), rejected=(), valid_count=0, report_bytes=b"xlsx-bytes"):
    report = tmp_path / "report_run-1.xlsx"
    report.write_bytes(report_bytes)
    return PipelineResult(
        run_id="run-1",
        report_path=report,
        valid_count=valid_count,
        violations=list(violations),
        rejected=list(rejected),
    )


def body_of(message):
    return message.get_body(preferencelist=("plain",)).get_content()


def simple_message():
    message = EmailMessage()
    message["Subject"] = "test"
    message.set_content("hello")
    return message


def test_subject_and_body_show_the_verdict_and_counts(tmp_path):
    result = make_result(
        tmp_path,
        violations=[make_violation("R1"), make_violation("R3", Severity.WARNING)],
        rejected=[make_rejected()],
        valid_count=5,
    )

    message = build_message(result, make_settings())

    assert message["Subject"] == "[BPA] ACTION REQUIRED - 2 exception(s), 1 rejected line(s)"
    body = body_of(message)
    assert "Run ID: run-1" in body
    assert "Result: ACTION REQUIRED" in body
    assert "Lines read: 6 (valid: 5, rejected: 1)" in body
    assert "Exceptions: 2 (blocking: 1, warnings: 1)" in body
    assert "attached" in body


def test_clear_result_is_announced_as_such(tmp_path):
    message = build_message(make_result(tmp_path, valid_count=3), make_settings())

    assert message["Subject"] == "[BPA] ALL CLEAR - 0 exception(s), 0 rejected line(s)"


def test_body_holds_no_personal_data(tmp_path):
    result = make_result(
        tmp_path, violations=[make_violation(name="Mbuyi")], rejected=[make_rejected()]
    )

    body = body_of(build_message(result, make_settings()))

    for text in ("Mbuyi", "M001", "R1 problem", "Acme"):
        assert text not in body


def test_report_is_attached_as_an_excel_file(tmp_path):
    message = build_message(make_result(tmp_path), make_settings())

    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report_run-1.xlsx"
    assert attachments[0].get_content_type() == XLSX_MIME
    assert attachments[0].get_content() == b"xlsx-bytes"


def test_sender_and_recipients_are_set(tmp_path):
    settings = make_settings(recipients=("a@example.com", "b@example.com"))

    message = build_message(make_result(tmp_path), settings)

    assert message["From"] == "bpa@example.com"
    assert message["To"] == "a@example.com, b@example.com"


def test_oversized_report_is_not_attached(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "MAX_ATTACHMENT_BYTES", 5)
    result = make_result(tmp_path, report_bytes=b"0123456789")

    message = build_message(result, make_settings())

    assert list(message.iter_attachments()) == []
    assert "too large" in body_of(message)


def test_missing_report_file_is_a_notification_error(tmp_path):
    result = make_result(tmp_path)
    result.report_path.unlink()

    with pytest.raises(NotificationError, match="Cannot read the report"):
        build_message(result, make_settings())


class FakeConnection:
    def __init__(self, owner, kind, host, port, timeout, context):
        self.owner = owner
        self.kind = kind
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.tls_context = None
        self.events = []
        self.credentials = None
        self.message = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        self.events.append("starttls")
        self.tls_context = context

    def login(self, username, password):
        if self.owner.login_error:
            raise self.owner.login_error
        self.events.append("login")
        self.credentials = (username, password)

    def send_message(self, message):
        if self.owner.send_error:
            raise self.owner.send_error
        self.events.append("send")
        self.message = message


class FakeSmtp:
    def __init__(self):
        self.opened = []
        self.login_error = None
        self.send_error = None

    def smtp(self, host, port, timeout=None):
        connection = FakeConnection(self, "smtp", host, port, timeout, None)
        self.opened.append(connection)
        return connection

    def smtp_ssl(self, host, port, timeout=None, context=None):
        connection = FakeConnection(self, "ssl", host, port, timeout, context)
        self.opened.append(connection)
        return connection


@pytest.fixture
def fake_smtp(monkeypatch):
    fake = FakeSmtp()
    monkeypatch.setattr(notify.smtplib, "SMTP", fake.smtp)
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", fake.smtp_ssl)
    return fake


def test_starttls_encrypts_before_login_and_checks_the_certificate(fake_smtp):
    message = simple_message()

    send_notification(message, make_settings())

    connection = fake_smtp.opened[0]
    assert connection.kind == "smtp"
    assert (connection.host, connection.port) == ("smtp.example.com", 587)
    assert connection.timeout == notify.SMTP_TIMEOUT_SECONDS

    assert connection.events == ["starttls", "login", "send"]
    assert connection.credentials == ("bpa-user", "smtp-secret")
    assert connection.tls_context.verify_mode == ssl.CERT_REQUIRED
    assert connection.tls_context.check_hostname is True
    assert connection.message is message


def test_ssl_mode_uses_an_encrypted_connection_from_the_start(fake_smtp):
    send_notification(simple_message(), make_settings(security="ssl", port=465))

    connection = fake_smtp.opened[0]
    assert connection.kind == "ssl"
    assert connection.events == ["login", "send"]
    assert connection.context.verify_mode == ssl.CERT_REQUIRED
    assert connection.context.check_hostname is True


def test_local_development_mode_sends_without_encryption_or_login(fake_smtp):
    settings = make_settings(
        security="none", host="127.0.0.1", port=1025, username=None, password=None
    )

    send_notification(simple_message(), settings)

    connection = fake_smtp.opened[0]
    assert connection.events == ["send"]
    assert connection.tls_context is None


def test_no_login_without_credentials(fake_smtp):
    send_notification(simple_message(), make_settings(username=None, password=None))

    assert fake_smtp.opened[0].events == ["starttls", "send"]


def test_connection_failure_becomes_a_notification_error(monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(notify.smtplib, "SMTP", refuse)

    with pytest.raises(NotificationError, match="Could not send") as error:
        send_notification(simple_message(), make_settings())

    assert "smtp-secret" not in str(error.value)


def test_refused_credentials_become_a_notification_error(fake_smtp):
    fake_smtp.login_error = smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    with pytest.raises(NotificationError, match="SMTPAuthenticationError") as error:
        send_notification(simple_message(), make_settings())

    assert "smtp-secret" not in str(error.value)
    assert fake_smtp.opened[0].events == ["starttls"]


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPRecipientsRefused({}),
        smtplib.SMTPServerDisconnected("connection lost"),
        TimeoutError("timed out"),
    ],
)
def test_delivery_failures_become_notification_errors(fake_smtp, error):
    fake_smtp.send_error = error

    with pytest.raises(NotificationError, match="Could not send"):
        send_notification(simple_message(), make_settings())

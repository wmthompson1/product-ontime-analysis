"""
sync_watcher.py
===============
Polls the `graph_sync_queue` SQLite sentinel table and triggers
graph_sync.sync_graph() whenever unprocessed rows appear.

The watcher is lightweight: it sleeps between polls and only calls
sync_graph() when the queue actually has pending entries, so it does
not generate unnecessary ArangoDB traffic.

Usage:
    # Run with defaults (poll every 30 s, log to stdout + sync_watcher.log)
    python hf-space-inventory-sqlgen/sync_watcher.py

    # Custom poll interval (seconds)
    python hf-space-inventory-sqlgen/sync_watcher.py --interval 60

    # Dry-run: detect changes but do NOT write to ArangoDB
    python hf-space-inventory-sqlgen/sync_watcher.py --dry-run

    # Run once (useful for cron / CI)
    python hf-space-inventory-sqlgen/sync_watcher.py --once

Environment variables honoured by graph_sync (passed through):
    ARANGO_HOST, ARANGO_DB, ARANGO_USER, ARANGO_ROOT_PASSWORD

Exit codes:
    0 — clean shutdown (SIGINT / --once with no failures)
    1 — at least one sync cycle failed
"""

import argparse
import json
import logging
import os
import signal
import smtplib
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "scripts")
DB_PATH = os.path.join(SCRIPT_DIR, "app_schema", "manufacturing.db")
LOG_PATH = os.path.join(SCRIPT_DIR, "sync_watcher.log")

DEFAULT_POLL_INTERVAL = 30
BATCH_MARK_SQL = """
    UPDATE graph_sync_queue
    SET processed = 1, processed_at = ?, sync_outcome = ?
    WHERE processed = 0
"""
PENDING_SQL = "SELECT COUNT(*) FROM graph_sync_queue WHERE processed = 0"
QUEUE_EXISTS_SQL = (
    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_sync_queue'"
)


def _setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger("sync_watcher")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    try:
        fh = logging.FileHandler(log_path)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        logger.warning("Could not open log file %s: %s", log_path, exc)

    return logger


def _pending_count(conn: sqlite3.Connection) -> int:
    row = conn.execute(PENDING_SQL).fetchone()
    return row[0] if row else 0


def _mark_processed(conn: sqlite3.Connection, outcome: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(BATCH_MARK_SQL, (now, outcome))
    conn.commit()


def _queue_table_exists(conn: sqlite3.Connection) -> bool:
    return conn.execute(QUEUE_EXISTS_SQL).fetchone() is not None


def run_sync(dry_run: bool, logger: logging.Logger, pending: int | None = None) -> bool:
    """
    Import and call graph_sync.sync_graph().
    Returns True on success, False on failure.
    Logs a concise alert summary to stderr on failure.

    pending — number of unprocessed queue rows at the time this sync was
              triggered; forwarded into _alert() for richer notifications.
    """
    sys.path.insert(0, SCRIPT_DIR)
    try:
        import graph_sync
    except ImportError as exc:
        logger.error("Cannot import graph_sync: %s", exc)
        _alert("IMPORT ERROR", str(exc), pending=pending)
        return False

    try:
        report = graph_sync.sync_graph(dry_run=dry_run)
    except Exception as exc:
        logger.error("Unhandled exception in sync_graph: %s", exc, exc_info=True)
        _alert("UNHANDLED EXCEPTION", str(exc), pending=pending)
        return False

    if report.success:
        logger.info(
            "Sync OK | vertices=%d edges=%d dry_run=%s",
            report.total_vertices,
            report.total_edges,
            dry_run,
        )
        if report.warnings:
            for w in report.warnings:
                logger.warning("sync warning: %s", w)
        return True
    else:
        logger.error("Sync FAILED:")
        for err in report.errors:
            logger.error("  %s", err)
        _alert("SYNC FAILED", "\n".join(report.errors), pending=pending)
        return False


def _alert(title: str, body: str, pending: int | None = None) -> None:
    """
    Failure alerting hook.

    Always writes a structured line to stderr so that log-shipping pipelines
    (Datadog, CloudWatch, etc.) can pick it up.

    When GRAPH_SYNC_ALERT_WEBHOOK is set, also POSTs a Slack-compatible
    incoming-webhook message containing:
      - timestamp (UTC ISO-8601)
      - alert title and error text
      - count of pending queue rows (when available)

    When GRAPH_SYNC_ALERT_EMAIL is set (comma-separated recipients), also
    sends an SMTP email using SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD.

    Leave both env vars empty (or unset) to keep the stderr-only behaviour.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pending_str = f"{pending} pending queue row(s)" if pending is not None else "pending count unavailable"

    stderr_line = f"[GRAPH_SYNC_ALERT] {ts} | {title} | pending={pending_str} | {body}"
    print(stderr_line, file=sys.stderr)

    webhook_url = os.environ.get("GRAPH_SYNC_ALERT_WEBHOOK", "").strip()
    if webhook_url:
        slack_text = (
            f":rotating_light: *Graph Sync Alert — {title}*\n"
            f"*Time:* {ts}\n"
            f"*Pending queue rows:* {pending_str}\n"
            f"*Details:*\n```{body}```"
        )
        payload = json.dumps({"text": slack_text}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status not in (200, 204):
                    print(
                        f"[GRAPH_SYNC_ALERT] Webhook POST returned HTTP {resp.status}",
                        file=sys.stderr,
                    )
        except urllib.error.URLError as exc:
            print(
                f"[GRAPH_SYNC_ALERT] Webhook POST failed: {exc}",
                file=sys.stderr,
            )

    _alert_email(title, body, ts, pending_str)


def _alert_email(title: str, body: str, ts: str, pending_str: str) -> None:
    """
    Send an SMTP email alert when GRAPH_SYNC_ALERT_EMAIL is set.

    Required env vars:
        GRAPH_SYNC_ALERT_EMAIL  — comma-separated recipient addresses
        SMTP_HOST               — SMTP server hostname
        SMTP_USER               — login username (also used as From address)
        SMTP_PASSWORD           — login password

    Optional env vars:
        SMTP_PORT               — SMTP port (default: 587, uses STARTTLS)

    Falls back silently when any required variable is missing.
    """
    recipients_raw = os.environ.get("GRAPH_SYNC_ALERT_EMAIL", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()

    if not (recipients_raw and smtp_host and smtp_user and smtp_password):
        return

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        return

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    subject = f"[Graph Sync Alert] {title}"
    email_body = (
        f"Graph Sync Alert — {title}\n"
        f"\n"
        f"Time:              {ts}\n"
        f"Pending queue rows: {pending_str}\n"
        f"\n"
        f"Details:\n"
        f"{body}\n"
    )

    msg = MIMEText(email_body, "plain")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipients, msg.as_string())
    except Exception as exc:
        print(
            f"[GRAPH_SYNC_ALERT] Email send failed: {exc}",
            file=sys.stderr,
        )


def _auto_install_triggers(conn: sqlite3.Connection, logger: logging.Logger) -> None:
    """
    Import install_sync_triggers and call install() on the open connection.
    This is called when sync_watcher detects that graph_sync_queue is absent,
    so a fresh database never silently skips trigger installation.
    """
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    try:
        import install_sync_triggers as ist
        ist.install(conn)
        logger.info("Sync triggers auto-installed successfully.")
    except Exception as exc:
        logger.error("Failed to auto-install sync triggers: %s", exc, exc_info=True)
        _alert("TRIGGER AUTO-INSTALL FAILED", str(exc))


def watch(poll_interval: int, dry_run: bool, once: bool, logger: logging.Logger) -> int:
    had_failure = False

    if not os.path.exists(DB_PATH):
        logger.error("Database not found at %s — install triggers first.", DB_PATH)
        return 1

    logger.info(
        "sync_watcher starting | db=%s interval=%ds dry_run=%s once=%s",
        DB_PATH,
        poll_interval,
        dry_run,
        once,
    )

    # Startup trigger health check — log clearly so operators can confirm
    # the system is healthy without waiting for the first poll cycle (#63).
    try:
        with sqlite3.connect(DB_PATH) as _chk:
            if _queue_table_exists(_chk):
                _trigger_count = _chk.execute(
                    "SELECT COUNT(*) FROM sqlite_master "
                    "WHERE type='trigger' AND name LIKE 'trg_arango_sync_%'"
                ).fetchone()[0]
                logger.info(
                    "Sync triggers verified — graph_sync_queue present with %d trigger(s).",
                    _trigger_count,
                )
            else:
                logger.warning(
                    "Startup health: graph_sync_queue table NOT found — "
                    "triggers will be auto-installed on the first poll cycle."
                )
    except Exception as _chk_exc:
        logger.warning("Could not verify trigger health at startup: %s", _chk_exc)

    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down.", signum)
        sys.exit(0 if not had_failure else 1)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            try:
                if not _queue_table_exists(conn):
                    logger.warning(
                        "graph_sync_queue table not found — auto-installing sync triggers."
                    )
                    _auto_install_triggers(conn, logger)
                else:
                    count = _pending_count(conn)
                    if count > 0:
                        logger.info(
                            "%d pending change(s) detected — running sync.", count
                        )
                        ok = run_sync(dry_run=dry_run, logger=logger, pending=count)
                        outcome = "SUCCESS" if ok else "FAILED"
                        if not dry_run:
                            _mark_processed(conn, outcome)
                        if not ok:
                            had_failure = True
                    else:
                        logger.debug("No pending changes.")
            finally:
                conn.close()
        except Exception as exc:
            logger.error("Poll cycle error: %s", exc, exc_info=True)
            _alert("POLL CYCLE ERROR", str(exc))
            had_failure = True

        if once:
            break

        time.sleep(poll_interval)

    return 1 if had_failure else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch graph_sync_queue and auto-sync SQLite → ArangoDB."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        help=f"Poll interval in seconds (default: {DEFAULT_POLL_INTERVAL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect changes but do not write to ArangoDB",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one poll cycle then exit (useful for cron / CI)",
    )
    parser.add_argument(
        "--log",
        default=LOG_PATH,
        help=f"Path to log file (default: {LOG_PATH})",
    )
    args = parser.parse_args()

    logger = _setup_logging(args.log)
    exit_code = watch(
        poll_interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
        logger=logger,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

"""The stock alert job (FR-26, hld.md §3.6): compare a store's stock with its previous version,
and email the store manager about every product that crossed into low or out.

    python -m notify.run --store data/SBY-DEMO-001 --before <git ref>   # on a push
    python -m notify.run --store data/SBY-DEMO-001 --current             # switching alerts on
    ... --dry-run                                                        # print, send nothing

Settings come from the environment — in GitHub Actions, repository secrets: AGENTMAIL_API_KEY,
AGENTMAIL_INBOX_ID (the sending address) and STORE_MANAGER_EMAIL. None of them is in the
repository, which is public.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from notify.mail import AgentMailSender, PrintSender
from services.stock_alerts import changes, emails
from validation import load_store

SETTINGS = ("AGENTMAIL_API_KEY", "AGENTMAIL_INBOX_ID", "STORE_MANAGER_EMAIL")


def _stock_from(folder: Path, stock_csv: str):
    """The store as it was: the current folder with the earlier stock file swapped in."""
    with tempfile.TemporaryDirectory() as tmp:
        then = Path(tmp) / folder.name
        shutil.copytree(folder, then)
        (then / "stock.csv").write_text(stock_csv)
        return load_store(then).stock


def _previous(folder: Path, args) -> dict | None:
    if args.current:
        return None
    if args.before_file:
        return _stock_from(folder, Path(args.before_file).read_text())
    shown = subprocess.run(["git", "show", f"{args.before}:{folder.as_posix().strip('/')}/stock.csv"],
                           capture_output=True, text=True)  # fmt: skip
    return _stock_from(folder, shown.stdout) if shown.returncode == 0 else None  # a new store


def main(argv=None, sender=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", required=True, help="the store folder, e.g. data/SBY-DEMO-001")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--before", help="git ref of the previous version")
    group.add_argument("--before-file", help="a previous stock.csv")
    group.add_argument("--current", action="store_true", help="report everything low or out now")
    ap.add_argument("--dry-run", action="store_true", help="print the emails, send nothing")
    args = ap.parse_args(argv)

    folder = Path(args.store)
    after = load_store(folder)
    mails = emails(changes(_previous(folder, args), after), after)
    if not mails:
        print(f"{after.info.store_id}: no product crossed into low or out — nothing to send")
        return 0

    missing = [k for k in SETTINGS if not os.environ.get(k)]
    if args.dry_run:
        sender, to = sender or PrintSender(), os.environ.get("STORE_MANAGER_EMAIL", "(manager)")
    elif missing:
        print(f"Not sent: set {', '.join(missing)} (repository secrets).", file=sys.stderr)
        return 2
    else:
        to = os.environ["STORE_MANAGER_EMAIL"]
        sender = sender or AgentMailSender(os.environ["AGENTMAIL_API_KEY"],
                                           os.environ["AGENTMAIL_INBOX_ID"])  # fmt: skip

    version = os.environ.get("GITHUB_SHA", "local")[:12]
    mode = "current" if args.current else "change"
    try:
        for mail in mails:
            key = f"{after.info.store_id}-{version}-{mode}-{mail.kind}"
            sender.send(to, mail.subject, mail.text, mail.html, key)
            print(f"{'would send' if args.dry_run else 'sent'}: {mail.subject}")
    except Exception as exc:  # the job fails visibly; a re-run sends once (EC-58)
        print(f"Sending failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

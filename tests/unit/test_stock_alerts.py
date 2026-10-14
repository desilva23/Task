"""FR-26, AC-29 — the store manager is emailed when stock runs low and when it runs out.

Each test starts from the generated demo store, changes its stock file, and compares the two
versions, as the alert job does on a push (A-08). A fake sender stands in for AgentMail.
"""

import shutil

import pytest

from config import LOW_STOCK_UNITS
from notify import run
from services.stock_alerts import LOW, OUT, changes, emails
from validation import load_store


def ranged_with(store, units_above: int) -> list[str]:
    return [r["sku"] for r in store.rows("stock.csv")
            if r["ranged"] == "true" and r["shelf_qty"] and int(r["shelf_qty"]) > units_above]  # fmt: skip


@pytest.fixture
def versions(store, tmp_path):
    """The store as it was (a copy) and the folder whose stock the test then changes."""
    before = tmp_path / "before" / store.path.name  # V-11: the folder is named after the store
    shutil.copytree(store.path, before)
    return load_store(before), store


def old_stock(store, tmp_path) -> str:
    return str(tmp_path / "before" / store.path.name / "stock.csv")


def set_qty(store, sku, qty):
    store.edit("stock.csv", {"sku": sku}, shelf_qty=str(qty))


def test_ac_29_one_low_one_out_gives_one_email_of_each(versions):
    before, store = versions
    low, out = ranged_with(store, LOW_STOCK_UNITS)[:2]
    set_qty(store, low, LOW_STOCK_UNITS)
    set_qty(store, out, 0)
    after = load_store(store.path)
    found = changes(before.stock, after)
    assert {(a.kind, a.sku) for a in found} == {(LOW, low), (OUT, out)}
    mails = emails(found, after)
    assert [m.kind for m in mails] == [LOW, OUT]
    low_mail, out_mail = mails
    product = after.products[low]
    assert product.name in low_mail.text and f"{LOW_STOCK_UNITS} left" in low_mail.text
    assert "Floor " in low_mail.text and "shelf " in low_mail.text  # where to look
    assert after.products[out].name in out_mail.subject and "Out of stock" in out_mail.subject
    assert product.name in low_mail.html and "<script" not in low_mail.html


def test_ec_55_low_to_out_is_one_out_alert(versions):
    before, store = versions
    sku = next(s for s in ranged_with(store, 0) if 0 < before.stock[s].shelf_qty <= LOW_STOCK_UNITS)
    set_qty(store, sku, 0)
    assert [(a.kind, a.sku) for a in changes(before.stock, load_store(store.path))] == [(OUT, sku)]


def test_ec_56_staying_low_or_recovering_sends_nothing(versions):
    before, store = versions
    already_low = [s for s in ranged_with(store, 0) if before.stock[s].shelf_qty <= LOW_STOCK_UNITS]
    set_qty(store, already_low[0], max(1, before.stock[already_low[0]].shelf_qty - 1))  # stays low
    already_out = [k for k, p in before.stock.items() if p.ranged and p.shelf_qty == 0]
    set_qty(store, already_out[0], 40)  # recovers
    assert changes(before.stock, load_store(store.path)) == []


def test_ec_57_a_product_not_stocked_here_is_never_alerted(versions):
    before, store = versions
    sku = ranged_with(store, LOW_STOCK_UNITS)[0]  # well stocked, then delisted here
    store.edit("stock.csv", {"sku": sku}, ranged="false", shelf_qty="0")
    assert changes(before.stock, load_store(store.path)) == []


def test_ec_60_no_crossing_no_email(versions):
    before, store = versions
    assert changes(before.stock, load_store(store.path)) == []
    assert emails([], before) == []


def test_fr_26_switching_on_lists_everything_already_low_or_out(versions):
    before, _ = versions
    found = changes(None, before)
    stocked = {k: p for k, p in before.stock.items() if p.ranged}
    assert {a.sku for a in found if a.kind == OUT} == {
        k for k, p in stocked.items() if p.shelf_qty == 0
    }
    assert {a.sku for a in found if a.kind == LOW} == {
        k for k, p in stocked.items() if 0 < p.shelf_qty <= LOW_STOCK_UNITS
    }


class FakeSender:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, to, subject, text, html, key):
        if self.fail:
            raise RuntimeError("503 from the mail service")
        self.sent.append((to, subject, key))


SECRETS = {"AGENTMAIL_API_KEY": "am_test", "AGENTMAIL_INBOX_ID": "store23@agentmail.to",
           "STORE_MANAGER_EMAIL": "manager@example.com"}  # fmt: skip


def test_ac_29_the_job_sends_each_email_once_per_update(versions, tmp_path, monkeypatch):
    before, store = versions
    low, out = ranged_with(store, LOW_STOCK_UNITS)[:2]
    set_qty(store, low, 2)
    set_qty(store, out, 0)
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    old = old_stock(store, tmp_path)
    first, second = FakeSender(), FakeSender()
    assert run.main(["--store", str(store.path), "--before-file", str(old)], sender=first) == 0
    assert run.main(["--store", str(store.path), "--before-file", str(old)], sender=second) == 0
    assert [to for to, _, _ in first.sent] == ["manager@example.com"] * 2
    keys = [key for _, _, key in first.sent]
    assert len(set(keys)) == 2 and keys == [
        key for _, _, key in second.sent
    ]  # same update, same keys


def test_ec_59_missing_settings_stop_the_job_and_send_nothing(
    versions, tmp_path, monkeypatch, capsys
):
    _, store = versions
    set_qty(store, ranged_with(store, LOW_STOCK_UNITS)[0], 0)
    for k in SECRETS:
        monkeypatch.delenv(k, raising=False)
    sender = FakeSender()
    code = run.main(["--store", str(store.path), "--before-file",
                     old_stock(store, tmp_path)], sender=sender)  # fmt: skip
    assert code == 2 and sender.sent == []
    assert "AGENTMAIL_API_KEY" in capsys.readouterr().err


def test_ec_59_a_dry_run_prints_instead_of_sending(versions, tmp_path, monkeypatch, capsys):
    _, store = versions
    set_qty(store, ranged_with(store, LOW_STOCK_UNITS)[0], 0)
    for k in SECRETS:
        monkeypatch.delenv(k, raising=False)
    code = run.main(["--store", str(store.path), "--before-file",
                     old_stock(store, tmp_path), "--dry-run"])  # fmt: skip
    assert code == 0 and "Out of stock" in capsys.readouterr().out


def test_ec_58_a_failed_send_fails_the_job(versions, tmp_path, monkeypatch):
    _, store = versions
    set_qty(store, ranged_with(store, LOW_STOCK_UNITS)[0], 0)
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    code = run.main(["--store", str(store.path), "--before-file",
                     old_stock(store, tmp_path)], sender=FakeSender(fail=True))  # fmt: skip
    assert code == 1


def test_a_08_the_job_reads_the_previous_version_from_git(store, tmp_path, monkeypatch):
    """A-08 — on a push the job compares the stock file with the commit before it."""
    import subprocess

    repo = tmp_path / "repo"
    folder = repo / "data" / store.path.name
    shutil.copytree(store.path, folder)

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-q")
    git("-c", "user.email=t@example.com", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "stock as it was")
    rows = (folder / "stock.csv").read_text().splitlines()
    sku = next(r.split(",")[0] for r in rows[1:]
               if r.split(",")[1] == "true" and r.split(",")[2] and int(r.split(",")[2]) > 10)  # fmt: skip
    (folder / "stock.csv").write_text("\n".join(
        f"{sku},true,0" if r.startswith(f"{sku},") else r for r in rows) + "\n")  # fmt: skip
    monkeypatch.chdir(repo)
    sender = FakeSender()
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    assert run.main(["--store", f"data/{store.path.name}", "--before", "HEAD"], sender=sender) == 0
    assert len(sender.sent) == 1 and sender.sent[0][1].startswith("Out of stock")

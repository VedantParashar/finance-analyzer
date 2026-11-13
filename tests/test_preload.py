import threading

import pytest

from finance_analyzer import edgar, preload, store


@pytest.fixture
def calls(monkeypatch):
    """Record what the pre-load does, with no network, database or waiting."""
    made = {"loaded": [], "info": []}
    monkeypatch.setattr(preload, "PAUSE", 0)
    monkeypatch.setattr(store, "stored_tickers", lambda: ["MSFT"])

    def load(ticker):
        if ticker == "XOM":
            raise ValueError("XOM has no annual report")
        made["loaded"].append(ticker)

    monkeypatch.setattr(store, "load_company", load)
    monkeypatch.setattr(edgar, "fetch_company_info", made["info"].append)
    return made


def test_only_missing_companies_are_loaded_and_a_failure_does_not_stop_the_rest(calls, capsys):
    failed = preload.run(["MSFT", "XOM", "WMT", "KO"])
    assert calls["loaded"] == ["WMT", "KO"] and calls["info"] == ["WMT", "KO"]  # MSFT was already stored
    assert failed == {"XOM": "ValueError: XOM has no annual report"}
    assert "Pre-load: 2 of 3 missing companies loaded" in capsys.readouterr().out


def test_the_list_is_the_thirty_stress_test_companies():
    assert len(preload.TICKERS) == 30 == len(set(preload.TICKERS))


def test_a_download_is_swapped_in_whole(monkeypatch, tmp_path):
    """The file must never be visible half-written: it's written under another name, then renamed."""
    class Response:
        text = '{"ok": true}'
        def raise_for_status(self): pass
        def json(self): return {"ok": True}

    monkeypatch.setenv("SEC_USER_AGENT", "Test test@example.com")
    monkeypatch.setattr(edgar.httpx, "get", lambda *args, **kwargs: Response())
    target = tmp_path / "cache" / "file.json"
    edgar._download("https://example.com", target)
    assert target.read_text() == '{"ok": true}' and [p.name for p in target.parent.iterdir()] == ["file.json"]


def test_saving_takes_a_lock_so_a_page_view_and_the_pre_load_cannot_collide():
    assert isinstance(store._SAVING, type(threading.Lock()))

from __future__ import annotations

from scripts import source_health_check


def test_check_sources_uses_main_fetch_logic(monkeypatch):
    github_source = "https://github.com/example/project/commits/main/CHANGELOG.md.atom"
    bad_source = "https://broken.example/rss"

    monkeypatch.setattr(source_health_check.main, "load_sources", lambda _path: [github_source, bad_source])

    def fake_fetch(source, cutoff, per_source):
        if source == github_source:
            return (
                source,
                [
                    {
                        "title": "v1.2.3",
                        "link": "https://github.com/example/project/releases/tag/v1.2.3",
                        "summary": "release notes",
                        "published": "2026-03-03T00:00:00+00:00",
                    }
                ],
                None,
            )
        return source, [], "bozo"

    monkeypatch.setattr(source_health_check.main, "_fetch_single_source", fake_fetch)

    rows, failed = source_health_check.check_sources()
    assert len(rows) == 2
    assert failed == 1
    assert rows[0]["status"] == "OK"
    assert rows[0]["entries"] == "1"
    assert rows[1]["status"] == "FAIL"

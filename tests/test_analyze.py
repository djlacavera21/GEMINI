from pathlib import Path

from gemini_cloner.analyze import inventory
from gemini_cloner.report import render_report
from gemini_cloner.util import write_json


def test_inventory_reads_text(tmp_path: Path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "README.md").write_text("# demo\nhello", encoding="utf-8")
    (src / "app.py").write_text("print('ok')\n", encoding="utf-8")
    inv = inventory(src)
    assert inv["file_count_seen"] == 2
    assert "README.md" in inv["sample"]


def test_report_without_analysis(tmp_path: Path):
    write_json(
        tmp_path / "job.json",
        {
            "kind": "tree",
            "source": "/tmp/demo",
            "created_at": "2026-09-01T00:00:00Z",
            "worktree": str(tmp_path / "source"),
            "files": 1,
        },
    )
    text = render_report(tmp_path)
    assert "GEMINI clone report" in text
    assert (tmp_path / "REPORT.md").is_file()

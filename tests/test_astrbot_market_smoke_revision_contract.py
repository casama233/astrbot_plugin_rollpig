from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "astrbot-market-smoke.yml"


def test_market_smoke_validates_checked_out_revision_not_default_branch():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "git archive HEAD" in text
    assert "--worker" in text
    assert "--plugin-source-dir .cache/plugin-source" in text
    assert "official-worker-current-checkout" in text

    # The top-level official validator normalizes repo URLs and clones the
    # repository default branch. Each smoke run must therefore use its official
    # worker mode directly against the archived checkout instead.
    assert "--plugins-json .cache/rollpig-market-smoke.json" not in text


def test_market_smoke_covers_minimum_and_current_astrbot():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "astrbot_ref:" in text
    assert "- v4.26.0" in text
    assert "- master" in text
    assert 'git clone --depth 1 --branch "$ASTRBOT_REF"' in text
    assert "astrbot-market-smoke-report-${{ matrix.astrbot_ref }}" in text


def test_market_smoke_runs_for_core_python_and_storage_changes():
    text = WORKFLOW.read_text(encoding="utf-8")

    for path_pattern in (
        '"*.py"',
        '"storage/**"',
        '"services/**"',
        '"renderers/**"',
    ):
        assert path_pattern in text

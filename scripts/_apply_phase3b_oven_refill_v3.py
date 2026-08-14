from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
v2 = ROOT / "scripts" / "_apply_phase3b_oven_refill_v2.py"
exec(compile(v2.read_text(encoding="utf-8"), str(v2), "exec"), {"__name__": "__main__", "__file__": str(v2)})


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    source = target.read_text(encoding="utf-8")
    actual = source.count(old)
    if actual < count:
        raise SystemExit(f"{path}: marker missing ({actual} < {count}): {old[:100]!r}")
    target.write_text(source.replace(old, new, count), encoding="utf-8")


# New commands remain registered only in the real main.py Star entry.
replace(
    "tests/test_command_registration_boundary.py",
    "HELPERS = ['legacy_main.py', 'daily_report_feature.py', 'ex_variant_feature.py', 'roast_reservation_feature.py']",
    "HELPERS = ['legacy_main.py', 'daily_report_feature.py', 'ex_variant_feature.py', 'roast_reservation_feature.py', 'oven_refill_feature.py']",
)
replace(
    "tests/test_command_registration_boundary.py",
    '    "my_pigsty",\n    "pigsty_daily_report",\n',
    '    "my_pigsty",\n    "oven_refill",\n    "oven_refill_support",\n    "pigsty_daily_report",\n',
)
replace(
    "tests/test_v361_hotfix_contract.py",
    '    "roast_reservation_feature.py",\n)',
    '    "roast_reservation_feature.py",\n    "oven_refill_feature.py",\n)',
)

# Schema 7 is now the normalized storage contract.
replace(
    "tests/test_dashboard_sql_analytics.py",
    'assert overview["observability"]["schema_version"] == 5',
    'assert overview["observability"]["schema_version"] == 7',
)
replace(
    "tests/test_new_unlock_trend.py",
    "    assert version == 5",
    "    assert version == 7",
)
replace(
    "tests/test_sqlite_storage.py",
    '    assert manager.verify()["schema_version"] == 6',
    '    assert manager.verify()["schema_version"] == 7',
)
replace(
    "tests/test_sqlite_storage.py",
    "    assert version == 5",
    "    assert version == 7",
)
replace(
    "tests/test_sqlite_storage.py",
    '    assert verification["schema_version"] == 6',
    '    assert verification["schema_version"] == 7',
)
replace(
    "tests/test_sqlite_v3_primary.py",
    '    assert verification["schema_version"] == 6',
    '    assert verification["schema_version"] == 7',
)
replace(
    "tests/test_sqlite_v3_primary.py",
    '''        assert connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0] == 5
''',
    '''        versions = {
            int(row[0])
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        }
        assert 7 in versions
        assert 6 not in versions
''',
)

print("Phase 3B v3 patch and contract upgrades applied")

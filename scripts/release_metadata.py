from __future__ import annotations

from pathlib import Path
from string import ascii_letters, digits
from typing import Mapping


REQUIRED_FIELDS = ("name", "display_name", "version")
SAFE_PLUGIN_NAME = frozenset(ascii_letters + digits + "_.-")


def parse_metadata(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")

    missing = [name for name in REQUIRED_FIELDS if not fields.get(name)]
    if missing:
        raise ValueError(
            "metadata.yaml missing required fields: " + ", ".join(missing)
        )

    version = fields["version"]
    parts = version.split(".")
    if len(parts) != 3 or not all(part and part.isdigit() for part in parts):
        raise ValueError("metadata.yaml must contain a stable x.y.z version")

    plugin_name = fields["name"]
    if any(character not in SAFE_PLUGIN_NAME for character in plugin_name):
        raise ValueError("metadata.yaml contains an unsafe plugin name")
    return fields


def build_outputs(fields: Mapping[str, str]) -> dict[str, str]:
    version = fields["version"]
    plugin_name = fields["name"]
    return {
        "version": version,
        "tag": f"v{version}",
        "plugin_name": plugin_name,
        "display_name": fields["display_name"],
        "archive": f"{plugin_name}-v{version}.zip",
    }


def main() -> None:
    fields = parse_metadata(
        Path("metadata.yaml").read_text(encoding="utf-8")
    )
    for key, value in build_outputs(fields).items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

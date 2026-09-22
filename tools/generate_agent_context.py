"""Generate portable AI context artifacts from ``pyincucyte.context``."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyincucyte import context  # noqa: E402


def main() -> None:
    artifact = context.export_context()
    package_dir = ROOT / "pyincucyte"
    readme = "# PyIncucyte AI context\n\n" + context.read() + "\n\n"
    readme += "## Public topics\n\n"
    readme += "\n".join(
        f"- `{topic['topic']}` — {topic['title']}: {topic['description']}"
        for topic in artifact["topics"]
    )
    readme += "\n\nRead the structured `pyincucyte_context.json` artifact or use "
    readme += "`from pyincucyte import context` for topic reads and search.\n"
    (ROOT / "README_AI.md").write_text(readme, encoding="utf-8")
    payload = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    (ROOT / "pyincucyte_context.json").write_text(payload, encoding="utf-8")
    (package_dir / "README_AI.md").write_text(readme, encoding="utf-8")
    (package_dir / "pyincucyte_context.json").write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()

## Release publication authorization

Jamie has authorized agents working in this repository to complete the deploy
contract, including GitHub release and Python Package Index (PyPI) publication,
and to use the already authenticated PyPI browser session for trusted publisher
management. Do not ask again for permission for these operations. Stop only if
authentication, multi-factor authentication, or an external account decision
is required.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current

## AI control layer

The public usage guide is `pyincucyte.context`, with portable copies in
`README_AI.md` and `pyincucyte_context.json`. Claude uses
`.claude/skills/pyincucyte/`; Codex uses `.codex/skills/pyincucyte/`. Both call
the same headless registry in `pyincucyte/actions.py`. Safe extensions are
guided by `.claude/skills/pyincucyte-extend/` and
`.codex/skills/pyincucyte-extend/`; guide maintenance is defined in
`.claude/skills/pyincucyte/reference/context-maintenance.md`.

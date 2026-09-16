"""Build-time, idempotent edits for the reviewed hermes-otel 0.11.0 tree."""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/hermes/plugins/hermes_otel")
changes = {
    "__init__.py": (
        "    # Core hooks (always available)",
        '    import os\n    if os.getenv("HERMES_OTEL_USAGE_ONLY") == "true":\n'
        '        from .usage_contract import install\n        install(hooks)\n\n'
        "    # Core hooks (always available)",
    ),
    "tracer.py": (
        "                        provider.add_span_processor(processor)",
        '                        if os.getenv("HERMES_OTEL_USAGE_ONLY") == "true":\n'
        '                            from .usage_contract import UsageProcessor\n'
        '                            processor = UsageProcessor(processor)\n'
        "                        provider.add_span_processor(processor)",
    ),
}
for name, (old, new) in changes.items():
    path = root / name
    text = path.read_text(encoding="utf-8")
    if new in text:
        continue
    if text.count(old) != 1:
        raise SystemExit(f"Unsupported hermes-otel source: {name}")
    path.write_text(text.replace(old, new), encoding="utf-8")

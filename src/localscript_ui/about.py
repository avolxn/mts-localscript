from __future__ import annotations

import os
import platform
from importlib.metadata import version
from string import Template

import localscript_ui as toad
from localscript_ui import get_version, paths
from localscript_ui.app import ToadApp

ABOUT_TEMPLATE = Template(
    """\
# About ${PRODUCT} v${PRODUCT_VERSION}

${COMPANY}

Platform: ${PLATFORM}

Local terminal interface for the ${PRODUCT} coding agent.

## Config

config read from `$SETTINGS_PATH`

```json
$CONFIG
```

## Paths

| Name | Path |
| --- | --- |
| App data | `$DATA_PATH` |
| App state | `$STATE_PATH` |
| App logs | `$LOG_PATH` |


## System

| System | Version |
| --- | --- |
| Python | $PYTHON |
| OS | $SYSTEM_PLATFORM |
| Terminal | $TERMINAL |

## Dependencies

| Library | Version |
| --- | --- |
| LocalScript UI | $PRODUCT_VERSION |
| Textual | $TEXTUAL_VERSION |
| Rich | $RICH_VERSION |

## Environment

| Environment variable | Value |
| --- | --- |
| `SHELL` | $SHELL |
| `TERM` | $TERM |
| `COLORTERM` | $COLORTERM |
| `TERM_PROGRAM` | $TERM_PROGRAM |
| `TERM_PROGRAM_VERSION` | $TERM_PROGRAM_VERSION |
"""
)


def render(app: ToadApp) -> str:
    """Render about markdown.

    Returns:
        Markdown string.
    """

    try:
        config: str | None = app.settings_path.read_text()
    except Exception:
        config = None

    template_data = {
        "COLORTERM": os.environ.get("COLORTERM", ""),
        "COMPANY": toad.VENDOR,
        "CONFIG": config,
        "DATA_PATH": paths.get_data(),
        "LOG_PATH": paths.get_log(),
        "PLATFORM": toad.PLATFORM,
        "PRODUCT": toad.PRODUCT,
        "PRODUCT_VERSION": get_version(),
        "STATE_PATH": paths.get_state(),
        "SYSTEM_PLATFORM": platform.platform(),
        "PYTHON": f"{platform.python_implementation()} {platform.python_version()}",
        "RICH_VERSION": version("rich"),
        "SETTINGS_PATH": str(app.settings_path),
        "SHELL": os.environ.get("SHELL", ""),
        "TERM_PROGRAM_VERSION": os.environ.get("TERM_PROGRAM_VERSION", ""),
        "TERM_PROGRAM": os.environ.get("TERM_PROGRAM", ""),
        "TERM": os.environ.get("TERM", ""),
        "TEXTUAL_VERSION": version("textual"),
        "TERMINAL": app.term_program,
    }
    return ABOUT_TEMPLATE.safe_substitute(template_data)

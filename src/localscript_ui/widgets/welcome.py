from __future__ import annotations

from textual import containers
from textual.app import ComposeResult
from textual.widgets import Label, Markdown

ASCII_TOAD = r"""
  __  __ __        ______
 |  \/  |\ \      / / ___|
 | |\/| | \ \ /\ / /\___ \
 | |  | |  \ V  V /  ___) |
 |_|  |_|   \_/\_/  |____/
"""


WELCOME_MD = """\
## LocalScript

MWS Web Services (MWS)
Platform: **MWS Octapi**
Product: **LocalScript**
"""


class Welcome(containers.Vertical):
    def compose(self) -> ComposeResult:
        with containers.Center():
            yield Label(ASCII_TOAD, id="logo")
        yield Markdown(WELCOME_MD, id="message", classes="note")

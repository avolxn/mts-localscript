from __future__ import annotations

from typing import NamedTuple


class VersionMeta(NamedTuple):
    """Information about the current version of the LocalScript UI."""

    version: str
    upgrade_message: str
    visit_url: str


class VersionCheckFailed(Exception):
    """Something went wrong in the version check."""


async def check_version() -> tuple[bool, VersionMeta]:
    """Version checks are disabled for the vendored LocalScript UI.

    Returns:
        A tuple containing a boolean that indicates if there is a newer version,
            and a `VersionMeta` structure with meta information.
    """
    from localscript_ui import get_version

    version_meta = VersionMeta(
        version=get_version(),
        upgrade_message="",
        visit_url="",
    )
    return False, version_meta


if __name__ == "__main__":

    async def run() -> None:
        result = await check_version()
        from rich import print

        print(result)

    import asyncio

    asyncio.run(run())

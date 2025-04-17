"""discountscraper.utils.splash
===================================
Utilities related to *Splash* (the JS‑rendering service).

The goal is to keep the Lua script and the SplashRequest builder in a
dedicated module so that spiders stay *thin* and focused on extraction
logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from scrapy_splash import SplashRequest


#: Default *desktop* user agent.
DEFAULT_UA: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

#: Path to the Lua script bundled with this package.
_LUA_PATH = Path(__file__).with_suffix(".lua")


def load_lua_script() -> str:
    """Load the bundled Lua script from disk.

    The Lua script is stored next to this file with the same base name
    (``splash.lua``). Splitting it out of the Python source allows for
    simpler editing and syntax highlighting.
    """
    return _LUA_PATH.read_text(encoding="utf-8")


def build_splash_request(
    url: str,
    *,
    callback,
    endpoint: str = "execute",
    splash_args: Dict[str, Any] | None = None,
    **kwargs,
) -> SplashRequest:
    """Return a :class:`scrapy_splash.SplashRequest` with sane defaults."""
    splash_args = splash_args or {}
    splash_args.setdefault("lua_source", load_lua_script())
    splash_args.setdefault("timeout", 90)
    splash_args.setdefault("wait", 3.0)

    return SplashRequest(
        url=url,
        callback=callback,
        endpoint=endpoint,
        args=splash_args,
        **kwargs,
    )

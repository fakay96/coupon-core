"""Utilities for integrating with Splash (JS renderer).

This module provides helpers to load Lua scripts and build SplashRequests.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from scrapy_splash import SplashRequest

LUA_SCRIPT_PATH: Path = Path(__file__).parent / "scripts" / "render.lua"

def load_lua_script() -> str:
    """Load and return the Lua script for Splash.

    Returns:
        The contents of the Lua script file.
    """
    return LUA_SCRIPT_PATH.read_text(encoding="utf-8")

def make_splash_request(
    url: str,
    callback: Any,
    endpoint: str = "execute",
    splash_args: Dict[str, Any] | None = None,
    **kwargs: Any,
) -> SplashRequest:
    """Build a SplashRequest with sane defaults.

    Args:
        url: target URL to render.
        callback: callback function for the response.
        endpoint: Splash endpoint.
        splash_args: additional Splash args.
        kwargs: passed to SplashRequest.

    Returns:
        Configured SplashRequest.
    """
    args = dict(splash_args) if splash_args else {}
    args.setdefault("lua_source", load_lua_script())
    args.setdefault("timeout", 90)
    args.setdefault("wait", 3.0)
    return SplashRequest(url=url, callback=callback, endpoint=endpoint, args=args, **kwargs)

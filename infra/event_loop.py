"""
Infrastructure: Event loop setup with uvloop (Linux) or fallback (Windows/Mobile).
"""

from __future__ import annotations

import asyncio
import platform
import sys

from loguru import logger


def setup_event_loop() -> None:
    """
    Configure the best available event loop for the current platform.
    - Linux/Docker: use uvloop for maximum performance
    - Windows/Mobile: fallback to default asyncio
    """
    system = platform.system().lower()

    if system == "linux":
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("⚡ Event loop: uvloop (high-performance mode)")
            return
        except ImportError:
            logger.warning("uvloop not available on Linux, using default asyncio")
    elif system == "windows":
        # Windows uses ProactorEventLoop by default in Python 3.10+
        # SelectorEventLoop is more compatible with some libraries
        if sys.version_info >= (3, 10):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("⚡ Event loop: asyncio (Windows mode)")
        return
    else:
        logger.info(f"⚡ Event loop: asyncio (platform: {system})")


def detect_environment() -> dict:
    """Detect runtime environment capabilities."""
    env = {
        "platform": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "uvloop_available": False,
        "orjson_available": False,
        "is_docker": False,
        "is_mobile": False,
    }

    # Check uvloop
    try:
        import uvloop
        env["uvloop_available"] = True
    except ImportError:
        pass

    # Check orjson
    try:
        import orjson
        env["orjson_available"] = True
    except ImportError:
        pass

    # Check if running in Docker
    try:
        with open("/proc/1/cgroup", "r") as f:
            env["is_docker"] = "docker" in f.read() or "containerd" in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    # Detect mobile (ARM without Docker is likely Termux)
    if env["architecture"] in ("aarch64", "armv7l") and not env["is_docker"]:
        env["is_mobile"] = True

    return env

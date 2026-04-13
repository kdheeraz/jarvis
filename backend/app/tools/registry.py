import importlib
import pkgutil
from typing import Optional

from langchain_core.tools import BaseTool
from loguru import logger

from app.config import get_config

_discovered_tools: Optional[dict[str, BaseTool]] = None


def _discover_tools() -> dict[str, BaseTool]:
    """Auto-discover all tools in the builtin package."""
    global _discovered_tools
    if _discovered_tools is not None:
        return _discovered_tools

    import app.tools.builtin as builtin_pkg

    tools = {}
    for importer, modname, ispkg in pkgutil.iter_modules(builtin_pkg.__path__):
        module = importlib.import_module(f"app.tools.builtin.{modname}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, BaseTool):
                tools[attr.name] = attr
                logger.debug(f"Discovered tool: {attr.name}")

    _discovered_tools = tools
    logger.info(f"Discovered {len(tools)} tools: {list(tools.keys())}")
    return tools


def get_all_tools() -> dict[str, BaseTool]:
    """Get all discovered tools (enabled and disabled)."""
    return _discover_tools()


def get_active_tools() -> list[BaseTool]:
    """Get only the tools that are enabled in config."""
    config = get_config()
    all_tools = _discover_tools()
    enabled = config.tools.enabled

    active = [tool for name, tool in all_tools.items() if name in enabled]
    logger.debug(f"Active tools: {[t.name for t in active]}")
    return active


def reset_discovery():
    """Force re-discovery of tools (for testing)."""
    global _discovered_tools
    _discovered_tools = None

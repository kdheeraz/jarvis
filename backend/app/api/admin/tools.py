from fastapi import APIRouter, Depends, HTTPException

from app.auth.middleware import require_admin
from app.config import get_config, save_config, reload_config
from app.llm.agent import rebuild_agent
from app.schemas.tool import ToolOut, ToolUpdateRequest
from app.tools.registry import get_all_tools

router = APIRouter(prefix="/api/admin/tools", tags=["admin-tools"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[ToolOut])
def list_tools():
    config = get_config()
    all_tools = get_all_tools()
    enabled_names = config.tools.enabled

    return [
        ToolOut(
            name=name,
            description=tool.description,
            enabled=name in enabled_names,
        )
        for name, tool in all_tools.items()
    ]


@router.put("/{tool_name}")
def update_tool(tool_name: str, request: ToolUpdateRequest):
    all_tools = get_all_tools()
    if tool_name not in all_tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    config = get_config()
    enabled = set(config.tools.enabled)

    if request.enabled:
        enabled.add(tool_name)
    else:
        enabled.discard(tool_name)

    config.tools.enabled = list(enabled)
    save_config(config)
    reload_config()
    rebuild_agent()

    return {"status": "ok", "tool": tool_name, "enabled": request.enabled}

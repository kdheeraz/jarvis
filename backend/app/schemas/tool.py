from pydantic import BaseModel


class ToolOut(BaseModel):
    name: str
    description: str
    enabled: bool


class ToolUpdateRequest(BaseModel):
    enabled: bool

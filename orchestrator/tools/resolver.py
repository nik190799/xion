"""Tool resolver substrate for cognition tool-calling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass(frozen=True)
class ToolResult:
    name: str
    content: Any
    is_error: bool = False


@runtime_checkable
class ToolResolver(Protocol):
    resolver_id: str

    def list_tools(self) -> list[ToolSpec]: ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult: ...


__all__ = ["ToolResolver", "ToolResult", "ToolSpec"]

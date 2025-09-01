import asyncio
import argparse
from typing import Dict, List, Tuple

from langchain_mcp_adapters.client import MultiServerMCPClient


# Hardcode your MCP servers here. Key is the display name, value is the connection config.
# Add more entries as needed.
SERVERS: Dict[str, Dict[str, str]] = {
    # Provided MCP servers
    "ChefByte": {"transport": "sse", "url": "http://192.168.0.226:8052/sse"},
    "GeneralByte": {"transport": "sse", "url": "http://192.168.0.226:8050/sse"},
    "HomeAssistant": {"transport": "sse", "url": "http://192.168.0.226:8051/sse"},
    "CoachByte": {"transport": "sse", "url": "http://192.168.0.226:8053/sse"},
}


def _classify_group(tool_name: str) -> str:
    name = tool_name.strip().upper()
    if name.startswith("UPDATE"):
        return "Update tools"
    if name.startswith("GET"):
        return "Getter tools"
    if name.startswith("ACTION"):
        return "Actions tools"
    return "Other tools"


def _clean_desc(desc: str | None) -> str:
    if not desc:
        return ""
    # Collapse whitespace/newlines to single spaces for compactness
    return " ".join(str(desc).split())


def _strip_domain_prefix(tool_name: str, prefixes: list[str]) -> str:
    """Remove a known domain prefix (e.g., CHEF_, COACH_) from the tool name for display/classify."""
    if not tool_name:
        return tool_name
    for p in prefixes:
        if tool_name.upper().startswith(p + "_"):
            return tool_name[len(p) + 1 :]
    return tool_name


async def build_light_schema_text() -> str:
    client = MultiServerMCPClient(SERVERS)

    lines: List[str] = []

    for server_name in SERVERS.keys():
        # Fetch tools for this server only
        try:
            tools = await client.get_tools(server_name=server_name)
        except Exception as exc:
            lines.append(server_name)
            lines.append("Update tools")
            lines.append("Getter tools")
            lines.append("Actions tools")
            lines.append(f"- error: failed to load tools ({exc})")
            lines.append("")
            continue

        # Group tools by prefix
        grouped: Dict[str, List[Tuple[str, str]]] = {
            "Update tools": [],
            "Getter tools": [],
            "Actions tools": [],
            "Other tools": [],
        }
        # Domain prefixes we expect; strip these for classification/display
        domain_prefixes = ["COACH", "CHEF", "GENERAL", "HA"]
        for t in tools:
            tool_name = getattr(t, "name", "") or ""
            tool_desc = _clean_desc(getattr(t, "description", ""))
            short_name = _strip_domain_prefix(tool_name, domain_prefixes)
            grp = _classify_group(short_name)
            # store original and short name so we can show both if needed
            grouped.setdefault(grp, []).append((tool_name, short_name, tool_desc))

        # Sort each group alphabetically by tool name
        for grp_label in grouped:
            # sort by the short name (index 1); keep stable
            grouped[grp_label].sort(key=lambda x: x[1].lower())

        # Render in the requested order; only include non-empty groups
        lines.append(server_name)

        for grp_label in ("Update tools", "Getter tools", "Actions tools"):
            lines.append(grp_label)
            if grouped[grp_label]:
                for orig_name, short_name, desc in grouped[grp_label]:
                    # Keep the original full tool name (including domain prefix) in the summary
                    display = orig_name
                    if desc:
                        lines.append(f"- {display}: {desc}")
                    else:
                        lines.append(f"- {display}:")
            lines.append("")

        # Include unmatched tools, if any
        if grouped["Other tools"]:
            lines.append("Other tools")
            for orig_name, short_name, desc in grouped["Other tools"]:
                # Keep original full tool name for other tools as well
                display = orig_name
                if desc:
                    lines.append(f"- {display}: {desc}")
                else:
                    lines.append(f"- {display}:")
            lines.append("")

    # Join and return the text block
    # Strip trailing whitespace/newlines for a clean block
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and persist light schema text from MCP servers")
    parser.add_argument("--out", type=str, default="light_schema.txt", help="Output text file path")
    args = parser.parse_args()

    text = asyncio.run(build_light_schema_text())
    # Write to file
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote light schema to: {args.out}")


if __name__ == "__main__":
    main()



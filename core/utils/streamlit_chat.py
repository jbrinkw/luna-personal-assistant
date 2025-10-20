"""Streamlit Chat Interface with Agent Selection.

A chat interface that discovers Luna agents and uses them with MCP server tools.
Supports agent selection and full chat history.
"""
import os
import sys
import json
import asyncio
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root importability
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import streamlit as st

from core.utils.extension_discovery import discover_extensions
from core.utils.db import fetch_all_memories


# ============================================================================
# Agent Discovery
# ============================================================================

def discover_agents() -> Dict[str, Any]:
    """Discover all available agents in core/agents/.
    
    Returns:
        Dict mapping agent_name -> agent_module with run_agent function
    """
    agents = {}
    agents_dir = PROJECT_ROOT / 'core' / 'agents'
    
    if not agents_dir.exists():
        return agents
    
    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('_'):
            continue
        
        agent_file = agent_dir / 'agent.py'
        if not agent_file.exists():
            continue
        
        try:
            # Import the agent module
            spec = importlib.util.spec_from_file_location(
                f"agent_{agent_dir.name}",
                agent_file
            )
            if not spec or not spec.loader:
                continue
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if it has run_agent function
            if hasattr(module, 'run_agent'):
                agents[agent_dir.name] = module
        
        except Exception as e:
            st.sidebar.warning(f"Failed to load {agent_dir.name}: {str(e)}")
            continue
    
    return agents


# ============================================================================
# Memory Loading
# ============================================================================

def load_memories() -> Optional[str]:
    """Fetch all memories from database and format as string.
    
    Returns:
        Formatted memory string or None if no memories
    """
    try:
        memories = fetch_all_memories()
        if not memories:
            return None
        
        # Format as numbered list of memory contents
        memory_lines = [f"{i+1}. {mem['content']}" for i, mem in enumerate(memories)]
        return "\n".join(memory_lines)
    except Exception as e:
        st.sidebar.warning(f"Failed to load memories: {str(e)}")
        return None


# ============================================================================
# Tool Loading
# ============================================================================

def load_mcp_tools() -> Dict[str, Any]:
    """Load all MCP-enabled tools from enabled extensions only.
    
    Returns:
        Dict with tool metadata organized by extension
    """
    extensions = discover_extensions()
    tool_metadata = {}
    
    # Load master_config to check enabled state
    master_config_path = PROJECT_ROOT / 'core' / 'master_config.json'
    enabled_extensions = set()
    try:
        if master_config_path.exists():
            with open(master_config_path, 'r') as f:
                master_config = json.load(f)
                for ext_name, ext_config in master_config.get('extensions', {}).items():
                    if ext_config.get('enabled', True):
                        enabled_extensions.add(ext_name)
    except Exception:
        # If we can't load config, expose all extensions
        enabled_extensions = {ext.get('name') for ext in extensions}
    
    for ext in extensions:
        ext_name = ext.get('name', 'unknown')
        
        # Skip disabled extensions
        if ext_name not in enabled_extensions:
            continue
            
        tools = ext.get('tools', [])
        tool_configs = ext.get('tool_configs', {})
        
        for tool_fn in tools:
            tool_name = getattr(tool_fn, '__name__', '')
            tool_config = tool_configs.get(tool_name, {})
            
            # Only include MCP-enabled tools
            if not tool_config.get('enabled_in_mcp', False):
                continue
            
            # Get tool documentation
            tool_doc = getattr(tool_fn, '__doc__', '') or f"Tool: {tool_name}"
            
            tool_metadata[tool_name] = {
                'extension': ext_name,
                'description': tool_doc.strip().split('\n')[0],
                'enabled_in_mcp': True,
                'passthrough': tool_config.get('passthrough', False),
                'full_doc': tool_doc.strip()
            }
    
    return tool_metadata


# ============================================================================
# Streamlit UI
# ============================================================================

def init_session_state():
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tool_metadata" not in st.session_state:
        st.session_state.tool_metadata = {}
    if "agents" not in st.session_state:
        st.session_state.agents = {}
    if "selected_agent" not in st.session_state:
        st.session_state.selected_agent = None


def refresh_tools_and_agents():
    """Refresh MCP tools and agents."""
    with st.spinner("Loading agents and tools..."):
        # Load tools
        st.session_state.tool_metadata = load_mcp_tools()
        
        # Discover agents
        st.session_state.agents = discover_agents()
        
        # Set default agent if not set
        if not st.session_state.selected_agent and st.session_state.agents:
            st.session_state.selected_agent = list(st.session_state.agents.keys())[0]


def render_sidebar():
    """Render the sidebar with agent selector, tool list and controls."""
    st.sidebar.title("🌙 Luna Chat")
    
    # Agent selector
    st.sidebar.subheader("🤖 Agent")
    if st.session_state.agents:
        agent_names = list(st.session_state.agents.keys())
        current_idx = 0
        if st.session_state.selected_agent in agent_names:
            current_idx = agent_names.index(st.session_state.selected_agent)
        
        selected = st.sidebar.selectbox(
            "Select Active Agent",
            agent_names,
            index=current_idx,
            key="agent_selector"
        )
        
        if selected != st.session_state.selected_agent:
            st.session_state.selected_agent = selected
            st.rerun()
        
        # Show agent info
        st.sidebar.caption(f"Using: **{st.session_state.selected_agent}**")
    else:
        st.sidebar.warning("No agents found")
    
    st.sidebar.divider()
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh All", use_container_width=True):
        refresh_tools_and_agents()
        st.sidebar.success(f"✅ Loaded {len(st.session_state.agents)} agents, {len(st.session_state.tool_metadata)} tools!")
    
    st.sidebar.divider()
    
    # Display tools by extension
    st.sidebar.subheader("🛠️ MCP Tools")
    if not st.session_state.tool_metadata:
        st.sidebar.info("No MCP tools found. Click 'Refresh All' to load.")
    else:
        # Group by extension
        by_extension = {}
        for tool_name, metadata in st.session_state.tool_metadata.items():
            ext = metadata['extension']
            if ext not in by_extension:
                by_extension[ext] = []
            by_extension[ext].append((tool_name, metadata))
        
        # Display each extension
        for ext_name, tool_list in sorted(by_extension.items()):
            with st.sidebar.expander(f"📦 {ext_name} ({len(tool_list)})", expanded=False):
                for tool_name, metadata in sorted(tool_list):
                    st.markdown(f"**`{tool_name}`**")
                    st.caption(metadata['description'][:100] + "..." if len(metadata['description']) > 100 else metadata['description'])
                    st.markdown("---")


def render_chat():
    """Render the main chat interface."""
    # Header with current agent
    agent_name = st.session_state.selected_agent or "No Agent"
    st.title("💬 Luna Chat")
    st.caption(f"Using **{agent_name}** agent with MCP tools")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                with st.chat_message("user", avatar="🧑"):
                    st.markdown(content)
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)
                    
                    # Show traces if available
                    if "traces" in msg and msg["traces"]:
                        with st.expander("🔧 Tool Calls", expanded=False):
                            for trace in msg["traces"]:
                                st.json(trace)
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)
        
        # Check if agent is available
        if not st.session_state.selected_agent or not st.session_state.agents:
            with st.chat_message("assistant", avatar="🤖"):
                error_msg = "❌ No agent available. Please select an agent from the sidebar."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            return
        
        # Get selected agent module
        agent_module = st.session_state.agents[st.session_state.selected_agent]
        
        # Process with agent
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"🤔 {st.session_state.selected_agent} is thinking..."):
                try:
                    # Build chat history context
                    chat_history_lines = []
                    for msg in st.session_state.messages[:-1]:  # Exclude current prompt
                        if msg["role"] == "user":
                            chat_history_lines.append(f"User: {msg['content']}")
                        elif msg["role"] == "assistant":
                            chat_history_lines.append(f"Assistant: {msg['content']}")
                    
                    chat_history_str = "\n".join(chat_history_lines) if chat_history_lines else None
                    
                    # Load memories from database
                    memory_str = load_memories()
                    
                    # Run agent (async)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            agent_module.run_agent(
                                user_prompt=prompt,
                                chat_history=chat_history_str,
                                memory=memory_str,
                                tool_root=None
                            )
                        )
                    finally:
                        loop.close()
                    
                    # Extract response
                    response_text = result.final if hasattr(result, 'final') else str(result)
                    traces = result.traces if hasattr(result, 'traces') else []
                    
                    # Display response
                    st.markdown(response_text)
                    
                    # Show timing if available
                    if hasattr(result, 'response_time_secs'):
                        st.caption(f"⏱️ Response time: {result.response_time_secs:.2f}s")
                    
                    # Save to history
                    msg_data = {
                        "role": "assistant",
                        "content": response_text
                    }
                    
                    if traces:
                        msg_data["traces"] = [
                            {
                                "tool": t.tool,
                                "args": t.args,
                                "output": t.output[:200] + "..." if len(t.output) > 200 else t.output,
                                "duration": t.duration_secs
                            }
                            for t in traces
                        ]
                    
                    st.session_state.messages.append(msg_data)
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Luna Chat",
        page_icon="🌙",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize
    init_session_state()
    
    # Auto-load on first run
    if not st.session_state.agents and "first_load" not in st.session_state:
        refresh_tools_and_agents()
        st.session_state.first_load = True
    
    # Render UI
    render_sidebar()
    render_chat()
    
    # Footer
    st.sidebar.divider()
    
    # Show memory count
    try:
        memories = fetch_all_memories()
        memory_count = len(memories) if memories else 0
        st.sidebar.caption(f"🧠 Memories: {memory_count}")
    except Exception:
        st.sidebar.caption("🧠 Memories: N/A")
    
    st.sidebar.caption(f"💬 Messages: {len(st.session_state.messages)}")
    st.sidebar.caption(f"🤖 Agents: {len(st.session_state.agents)}")
    st.sidebar.caption(f"🛠️ Tools: {len(st.session_state.tool_metadata)}")
    
    if st.sidebar.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


if __name__ == "__main__":
    main()


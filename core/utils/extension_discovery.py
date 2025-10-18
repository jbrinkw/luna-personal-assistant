"""Extension discovery module for Luna.

Scans extensions directory for tools and metadata, replacing light_schema_gen from legacy code.
"""
import os
import sys
import json
import glob
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def discover_extensions(tool_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Discover all extensions and their tools.
    
    Args:
        tool_root: Optional custom root directory (defaults to 'extensions/')
        
    Returns:
        List of extension dictionaries with structure:
        {
            'name': str,
            'path': str,
            'tools': List[Callable],
            'system_prompt': str,
            'tool_configs': Dict[str, Dict],  # tool_name -> config
            'config': Dict  # extension config.json
        }
    """
    if tool_root is None:
        tool_root = str(PROJECT_ROOT / 'extensions')
    else:
        tool_root = str(Path(tool_root).resolve())
    
    if not os.path.isdir(tool_root):
        return []
    
    extensions = []
    
    # Find all extension directories (containing tools/ subdirectory)
    for ext_dir in glob.glob(os.path.join(tool_root, '*')):
        if not os.path.isdir(ext_dir):
            continue
        
        tools_dir = os.path.join(ext_dir, 'tools')
        if not os.path.isdir(tools_dir):
            continue
        
        ext_name = os.path.basename(ext_dir)
        
        # Load extension config if present
        config_path = os.path.join(ext_dir, 'config.json')
        ext_config = {}
        if os.path.isfile(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    ext_config = json.load(f)
            except Exception:
                pass
        
        # Load tool_config.json
        tool_config_path = os.path.join(tools_dir, 'tool_config.json')
        tool_configs = {}
        if os.path.isfile(tool_config_path):
            try:
                with open(tool_config_path, 'r', encoding='utf-8') as f:
                    tool_configs = json.load(f)
            except Exception:
                pass
        
        # Find all *_tools.py files
        tool_files = glob.glob(os.path.join(tools_dir, '*_tools.py'))
        
        tools: List[Callable] = []
        system_prompt = ""
        
        for tool_file in tool_files:
            try:
                # Import the module
                module_name = os.path.splitext(os.path.basename(tool_file))[0]
                spec = importlib.util.spec_from_file_location(module_name, tool_file)
                if not spec or not spec.loader:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Extract TOOLS list
                if hasattr(module, 'TOOLS'):
                    module_tools = getattr(module, 'TOOLS')
                    if isinstance(module_tools, list):
                        for tool in module_tools:
                            if callable(tool):
                                tools.append(tool)
                
                # Extract SYSTEM_PROMPT (use first one found)
                if not system_prompt and hasattr(module, 'SYSTEM_PROMPT'):
                    sp = getattr(module, 'SYSTEM_PROMPT')
                    if isinstance(sp, str) and sp.strip():
                        system_prompt = sp.strip()
                    elif callable(sp):
                        # Some legacy code has SYSTEM_PROMPT as a function
                        try:
                            result = sp()
                            if isinstance(result, str) and result.strip():
                                system_prompt = result.strip()
                        except Exception:
                            pass
            
            except Exception:
                # Skip files that fail to load
                continue
        
        if tools:  # Only add extensions that have at least one tool
            extensions.append({
                'name': ext_name,
                'path': ext_dir,
                'tools': tools,
                'system_prompt': system_prompt,
                'tool_configs': tool_configs,
                'config': ext_config,
            })
    
    return extensions


def discover_extension_uis(tool_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Discover extension UIs that provide a start.sh entrypoint.

    Returns a list of dicts: { 'name': str, 'ui_path': str, 'start': str }
    """
    if tool_root is None:
        tool_root = str(PROJECT_ROOT / 'extensions')
    else:
        tool_root = str(Path(tool_root).resolve())

    results: List[Dict[str, Any]] = []
    if not os.path.isdir(tool_root):
        return results

    for ext_dir in glob.glob(os.path.join(tool_root, '*')):
        if not os.path.isdir(ext_dir):
            continue
        ui_dir = os.path.join(ext_dir, 'ui')
        start_sh = os.path.join(ui_dir, 'start.sh')
        if os.path.isdir(ui_dir) and os.path.isfile(start_sh):
            results.append({
                'name': os.path.basename(ext_dir),
                'ui_path': ui_dir,
                'start': start_sh,
            })
    return results


def discover_extension_services(tool_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Discover extension services defined under services/* with start.sh and service_config.json.

    Returns a list of dicts: { 'extension': str, 'service': str, 'path': str, 'start': str, 'config': Dict }
    """
    if tool_root is None:
        tool_root = str(PROJECT_ROOT / 'extensions')
    else:
        tool_root = str(Path(tool_root).resolve())

    results: List[Dict[str, Any]] = []
    if not os.path.isdir(tool_root):
        return results

    for ext_dir in glob.glob(os.path.join(tool_root, '*')):
        if not os.path.isdir(ext_dir):
            continue
        services_root = os.path.join(ext_dir, 'services')
        if not os.path.isdir(services_root):
            continue
        for svc_dir in glob.glob(os.path.join(services_root, '*')):
            if not os.path.isdir(svc_dir):
                continue
            start_sh = os.path.join(svc_dir, 'start.sh')
            cfg_path = os.path.join(svc_dir, 'service_config.json')
            if not os.path.isfile(start_sh) or not os.path.isfile(cfg_path):
                continue
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            results.append({
                'extension': os.path.basename(ext_dir),
                'service': os.path.basename(svc_dir),
                'path': svc_dir,
                'start': start_sh,
                'config': cfg,
            })
    return results


def build_all_light_schema() -> str:
    """Build a lightweight schema description of all available tools.
    
    Returns:
        String describing all tools in a format suitable for agent prompts
    """
    extensions = discover_extensions()
    
    lines = []
    for ext in extensions:
        ext_name = ext.get('name', 'unknown')
        tools = ext.get('tools', [])
        
        for tool in tools:
            tool_name = getattr(tool, '__name__', 'unknown')
            tool_doc = getattr(tool, '__doc__', '') or ''
            
            # Extract first line as summary
            doc_lines = tool_doc.strip().split('\n')
            summary = doc_lines[0].strip() if doc_lines else ''
            
            # Build tool signature from annotations
            try:
                import inspect
                sig = inspect.signature(tool)
                params = []
                for param_name, param in sig.parameters.items():
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else 'Any'
                    param_type_str = getattr(param_type, '__name__', str(param_type))
                    params.append(f"{param_name}: {param_type_str}")
                signature = f"{tool_name}({', '.join(params)})"
            except Exception:
                signature = f"{tool_name}(...)"
            
            lines.append(f"- {signature}")
            if summary:
                lines.append(f"  {summary}")
            lines.append("")
    
    return '\n'.join(lines)


def get_mcp_tools() -> List[Callable]:
    """Get all tools that are enabled for MCP exposure.
    
    Returns:
        List of tool functions that have enabled_in_mcp=true
    """
    extensions = discover_extensions()
    mcp_tools = []
    
    for ext in extensions:
        tools = ext.get('tools', [])
        tool_configs = ext.get('tool_configs', {})
        
        for tool in tools:
            tool_name = getattr(tool, '__name__', '')
            tool_config = tool_configs.get(tool_name, {})
            
            # Check if enabled in MCP (default to false for safety)
            if tool_config.get('enabled_in_mcp', False):
                mcp_tools.append(tool)
    
    return mcp_tools


"""
Utilities for loading and applying prompt templates.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# Base paths for prompts
SHARED_PROMPTS_DIR = Path(__file__).parent
BACKEND_PROMPTS_DIR = Path(__file__).parent.parent.parent / "backend" / "prompts"
MEETING_PROMPTS_DIR = Path(__file__).parent.parent.parent / "meeting_agent" / "prompts"


def get_prompt_path(
    prompt_name: str,
    agent_type: str = "shared",
    locale: str = "en",
) -> Optional[Path]:
    """
    Get the path to a prompt file.
    
    Args:
        prompt_name: Name of the prompt (without extension)
        agent_type: Type of agent ("shared", "pm", "meeting")
        locale: Locale code (e.g., "en", "vi", "zh_CN")
        
    Returns:
        Path to the prompt file, or None if not found
    """
    # Determine base directory
    if agent_type == "shared":
        base_dir = SHARED_PROMPTS_DIR / "common"
    elif agent_type == "pm":
        base_dir = BACKEND_PROMPTS_DIR
    elif agent_type == "meeting":
        base_dir = MEETING_PROMPTS_DIR
    else:
        base_dir = SHARED_PROMPTS_DIR / "common"
    
    # Try locale-specific first
    if locale != "en":
        locale_path = base_dir / f"{prompt_name}.{locale}.md"
        if locale_path.exists():
            return locale_path
    
    # Fall back to default
    default_path = base_dir / f"{prompt_name}.md"
    if default_path.exists():
        return default_path
    
    return None


def load_prompt(
    prompt_name: str,
    agent_type: str = "shared",
    locale: str = "en",
) -> Optional[str]:
    """
    Load a prompt template from file.
    
    Args:
        prompt_name: Name of the prompt
        agent_type: Type of agent
        locale: Locale code
        
    Returns:
        Prompt content as string, or None if not found
    """
    path = get_prompt_path(prompt_name, agent_type, locale)
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return None


def apply_template(
    template: str,
    variables: Dict[str, Any],
) -> str:
    """
    Apply variables to a prompt template.
    
    Uses Jinja2-style {{ variable }} syntax for simple substitution.
    
    Args:
        template: The prompt template
        variables: Dictionary of variables to substitute
        
    Returns:
        The rendered prompt
    """
    result = template
    
    # Add common variables
    all_vars = {
        "CURRENT_TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CURRENT_DATE": datetime.now().strftime("%Y-%m-%d"),
        **variables,
    }
    
    # Simple substitution ({{ variable }})
    for key, value in all_vars.items():
        result = result.replace("{{ " + key + " }}", str(value))
        result = result.replace("{{" + key + "}}", str(value))
    
    return result


def combine_prompts(*prompts: str, separator: str = "\n\n") -> str:
    """
    Combine multiple prompts into one.
    
    Args:
        *prompts: Prompts to combine
        separator: Separator between prompts
        
    Returns:
        Combined prompt
    """
    return separator.join(p for p in prompts if p)


def extract_sections(prompt: str) -> Dict[str, str]:
    """
    Extract named sections from a prompt.
    
    Sections are delimited by markdown headers (# Section Name).
    
    Args:
        prompt: The prompt to parse
        
    Returns:
        Dictionary of section name -> content
    """
    sections = {}
    current_section = "header"
    current_content = []
    
    for line in prompt.split("\n"):
        if line.startswith("# "):
            # Save previous section
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            # Start new section
            current_section = line[2:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = "\n".join(current_content).strip()
    
    return sections

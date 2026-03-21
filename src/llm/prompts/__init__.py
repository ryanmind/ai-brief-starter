"""Prompt loader for externalized prompt templates.

This module loads prompt templates from YAML files in the
same directory, allowing prompts to be edited independently of code.
"""
from __future__ import annotations

import os
import yaml
import logging

from typing import Dict

logger = logging.getLogger(__name__)

# Cache for loaded prompts
_prompt_cache: Dict[str, Dict[str, str]] = {}


def load_prompt(task_name: str) -> Dict[str, str]:
    """Load a prompt template for a given task.

    Loads from the file `{task_name}.yaml` in this directory.
    Results are cached after first load.

    Args:
        task_name: Name of the task (filename without .yaml extension)

    Returns:
        Dictionary with at least "system" and "user_template" keys.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        yaml.YAMLError: If the YAML is invalid
    """
    if task_name in _prompt_cache:
        return _prompt_cache[task_name].copy()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, f"{task_name}.yaml")

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_data = yaml.safe_load(f)

    if not isinstance(prompt_data, dict):
        raise ValueError(f"Prompt {task_name} must be a YAML dictionary")

    if "system" not in prompt_data or "user_template" not in prompt_data:
        raise ValueError(
            f"Prompt {task_name} must contain 'system' and 'user_template' keys"
        )

    _prompt_cache[task_name] = prompt_data
    return prompt_data.copy()


def clear_cache() -> None:
    """Clear the prompt cache."""
    _prompt_cache.clear()

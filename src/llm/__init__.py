"""LLM subpackage: cache, providers, client factory, prompt loading.

This subpackage contains the refactored LLM infrastructure:
- cache.py: Response caching with TTL
- client_factory.py: LLM client creation
- prompts/: External YAML prompt templates
- providers/: Abstract base and concrete implementations for different providers
"""

# Handle backward compatibility: re-export everything from the original llm.py module
# This is needed because the directory package shadows the module file
import sys
import importlib.util

# Load the original module file (src/llm.py)
spec = importlib.util.spec_from_file_location(
    "src_llm_py",
    sys.modules[__name__].__file__.replace("__init__.py", "../llm.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Re-export all public attributes
globals().update({k: v for k, v in vars(module).items() if not k.startswith('_')})

# Import and export our new subpackage content
from .cache import LLMResponseCache
from .client_factory import create_llm_client
from .prompts import load_prompt

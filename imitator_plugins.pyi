"""
convenient plugins API for imitator
you can generate this file using:
    `python3 imitator.py --generate-dev-pyi`
"""
from typing import Any, Literal

StateType = dict[str, Any]

HookAction = Literal[
    "before", "instead", "after", "init", "on_end",
    "on_full_end", "on_start", "on_interrupt_occur"
]
    
class TermIO:
    @staticmethod
    def getch(): ...

    @staticmethod
    def puts(s: str): ...

    @staticmethod
    def flush(): ...

class NextType:
    def __init__(self, frame_stack: list): ...

    def __call__(self, state: dict[str, Any]): ...

def add_hook(action: HookAction, hook):
    """Subscribes `hook` on `action` event"""

def hook(action: HookAction):
    """Wraps hook and subscribes on `action` event"""

def load_hook_from_file(path: str):
    """Loads hook from file located in `path`"""

def jput(s: str):
    """designed to write one symbol to stdout"""

def jprint(s: str):
    """designed to write text strings to stdout"""

def set_non_blocking_io(): ...
def set_blocking_io(): ...
def add_metadata(info: dict[str, str]): ...
def safe_open(path: str) -> str: ...

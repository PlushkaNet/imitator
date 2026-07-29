# !/usr/bin/python3
# ~~~ platform specific settings ~~~
import sys

CtrlC = "\x03"

class TermIO:
    @staticmethod
    def getch():
        return sys.stdin.read(1)

    @staticmethod
    def puts(s: str):
        sys.stdout.write(s)
    
    @staticmethod
    def flush():
        sys.stdout.flush()

try:
    import msvcrt

    TermIO.getch = msvcrt.getwch

    class RawTerminalSession:
        def __enter__(self):
            pass

        def __exit__(self, *_):
            pass

    def nonblockingio(func):
        return func

    def chkkeys():
        pass
except ImportError:
    import termios
    import tty
    import os

    class RawTerminalSession:
        __all__ = ["_fd", "_attr"]
        def __enter__(self):
            self._fd = sys.stdin.fileno()
            self._attr = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
        
        def __exit__(self, *_):
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._attr)
    
    def nonblockingio(func):
        def wrapper(*args, **kwargs):
            os.set_blocking(sys.stdin.fileno(), False)
            try:
                return func(*args, **kwargs)
            finally:
                os.set_blocking(sys.stdin.fileno(), True)
        return wrapper
    
    def chkkeys():
        if TermIO.getch() == CtrlC:
            raise KeyboardInterrupt()

# ~~~ internal IO methods
io = TermIO

def jput(s: str):
    if s == "\n":
        io.puts("\n\r")
    else:
        io.puts(s)
    io.flush()

def jprint(s: str):
    io.puts(s.replace("\n", "\n\r"))
    io.flush()

# ~~~ common IO methods ~~~
def fatal(msg: str):
    print(msg)
    exit(1)

def safe_open(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except PermissionError:
        fatal(f"Cannot read {path!r} due to permission error")
    except UnicodeDecodeError:
        fatal(f"Cannot read {path!r} due to errors while decoding UTF-8 text")
    except OSError as e:
        fatal(f"Cannot read {path!r} due to OSError: {e}")

# ~~~ hooks system ~~~
memory = {
    "meta": [], # for hook metainfo's
    "hooks": {
        "before": [],
        "instead": [],
        "after": [],
        "on_interrupt_occur": [],
        "init": [],
        "on_end": [],
        "on_full_end": [],
        "on_start": []
    }
}
class HookException(Exception):
    """Base class for all hook exceptions"""

class NoSuchAction(HookException):
    """Raised if hook tryes to add itself on unknown action"""

class UnknowMetaInfoDatatype(HookException):
    """Raised if author add incorrect matainfo type (such as int instead of dict)"""

def add_hook(action: str, hook):
    if action in memory["hooks"]:
        memory["hooks"][action].append(hook)
    else:
        raise NoSuchAction()

def hook(action: str):
    def wrapper(func):
        add_hook(action, func)
    return wrapper

def add_metadata(info: dict[str, str]):
    if not isinstance(info, dict):
        raise UnknowMetaInfoDatatype()
    memory["meta"].append(info)

def load_hook_from_file(path: str):
    code = safe_open(path)
    try:
        exec(code, globals={
            "add_hook":add_hook,
            "hook": hook,
            "add_metadata":add_metadata,
            "imitator_safe_open": safe_open,
            "load_hook_from_file": load_hook_from_file,
            "jput": jput,
            "jprint": jprint,
            "_io": io
        })
    except Exception as e:
        fatal(f"error was raised while loading hook {path!r}:\n{e}")

class _Next:
    __slots__ = ["_frame_stack"]
    def __init__(self, frame_stack: list, /):
        self._frame_stack = frame_stack
    
    def __call__(self, state: dict, /):
        if self._frame_stack:
            return self._frame_stack.pop()(self, state)
        return state

def execute_action(action: str, state: dict, /) -> tuple:
    return _Next(memory["hooks"][action][:])(state)

# ~~~ program logic ~~~
import time # for printer mode
import argparse # for main method

def simulate(content: str):
    """
    mutates `content`
    unsupport hooking right now
    """
    while True:
        if io.getch() == CtrlC:
            break
        if len(content) > 0:
            jput(content[0])
            content = content[1:]

@nonblockingio
def printer_body(state: dict) -> bool:
    """
    mutates `state`
    returns if was breaked by Ctrl+C or not
    """
    try:
        while state["content"]:
            ##########before##########
            state = execute_action("before", state)
            ##########################

            chkkeys() # linux only

            #########instead##########
            state = execute_action("instead", state)
            ###########################

            time.sleep(state["delay"])

            ###########after###########
            state = execute_action("after", state)
            ###########################
    except KeyboardInterrupt:
        state = execute_action("on_interrupt_occur", state)
        return True
    return False

def printer(state: dict):
    """mutates `content`"""
    state["printer_func"] = printer_body
    content = state["content"] # immutate
    state = execute_action("init", state)
    if state["loop"]:
        finish = state["printer_func"](state)
        while not finish:
            state = execute_action("on_end", state)
            if state.get("stop", False):
                break
            state["content"] = content # restore
            finish = state["printer_func"](state)
    else:
        state["printer_func"](state)
    execute_action("on_full_end", state)

# ~~~ default behaviour ~~~
@hook("instead")
def _printer_default_instead(_next, state: dict):
    state["_val"] = state["content"][0]
    jput(state["_val"])
    state["content"] = state["content"][1:]
    return _next(state)

# ~~~ main ~~~
def main():
    argparser = argparse.ArgumentParser("imitator")
    argparser.add_argument(
        "-f", "--file",
        action="store",
        type=str,
        help="file to read from"
    )
    argparser.add_argument(
        "-m", "--mode",
        action="store",
        type=str,
        choices=[
            "typer",
            "printer"
        ],
        help="mode to be executed",
        default=""
    )
    argparser.add_argument(
        "-i", "--include",
        action="append",
        help="include hooks directory/file",
        default=[]
    )
    argparser.add_argument(
        "-d", "--delay",
        action="store",
        type=float,
        help="delay for printer",
        default=0.01
    )
    argparser.add_argument(
        "-l", "--loop",
        action="store_true",
        help="loop printer or not"
    )

    args = argparser.parse_args()

    if args.include:
        import os
        def process(include: str):
            if os.path.isdir(include):
                for inc in os.listdir(include):
                    process(os.path.join(include, inc))
            else:
                load_hook_from_file(include)
        for include in args.include:
            process(include)

    state = {
        "loop": args.loop,
        "delay": args.delay,
        "mode": args.mode
    }
    state = execute_action("on_start", state)
    if not state.get("prevent_load", False):
        if args.file:
            state["content"] = safe_open(args.file)
        else:
            fatal("no file to load and hooks did not set any prevention flag")
    
    if not state.get("content", ""):
        fatal("no content set, probably to mistake in hooks")

    with RawTerminalSession():
        if not state["mode"] or state["mode"] == "typer":
            simulate(state["content"])
        elif state["mode"] == "printer":
            printer(state)
        else:
            fatal(f"no such mode: {args.mode!r}")

if __name__ == "__main__":
    main()

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
    
    def set_non_blocking_io():
        pass
    
    def set_blocking_io():
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
        __slots__ = ["_fd", "_attr"]
        def __enter__(self):
            self._fd = sys.stdin.fileno()
            self._attr = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
        
        def __exit__(self, *_):
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._attr)
    
    def set_non_blocking_io():
        os.set_blocking(sys.stdin.fileno(), False)
    
    def set_blocking_io():
        os.set_blocking(sys.stdin.fileno(), True)
    
    def nonblockingio(func):
        def wrapper(*args, **kwargs):
            set_non_blocking_io()
            try:
                return func(*args, **kwargs)
            finally:
                set_blocking_io()
        return wrapper
    
    def chkkeys():
        if TermIO.getch() == CtrlC:
            raise KeyboardInterrupt()

# ~~~ internal IO methods
io = TermIO

def jput(s: str):
    """designed to write one symbol to stdout"""
    if s == "\n":
        io.puts("\n\r")
    else:
        io.puts(s)
    io.flush()

def jprint(s: str):
    """designed to write text strings to stdout"""
    io.puts(s.replace("\n", "\n\r"))
    io.flush()

# ~~~ common IO methods ~~~
def fatal(msg: str):
    print(f"fatal: {msg}")
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

class UnknownMetaInfoDatatype(HookException):
    """Raised if author add incorrect matainfo type (such as int instead of dict)"""

import typing

HookAction = typing.Literal[
    "before", "instead", "after", "init", "on_end",
    "on_full_end", "on_start", "on_interrupt_occur"
]

StateType = dict[str, typing.Any]

def add_hook(action: HookAction, hook):
    """Subscribes `hook` on `action` event"""
    if action in memory["hooks"]:
        memory["hooks"][action].append(hook)
    else:
        raise NoSuchAction()

def hook(action: HookAction):
    """Wraps hook and subscribes on `action` event"""
    def wrapper(func):
        add_hook(action, func)
    return wrapper

def add_metadata(info: dict[str, str]):
    if not isinstance(info, dict):
        raise UnknownMetaInfoDatatype()
    memory["meta"].append(info)

def load_hook_from_file(path: str):
    """Loads hook from file located in `path`"""
    code = safe_open(path)
    try:
        namespace = {}
        exec(code, namespace, namespace)
    except Exception as e:
        fatal(f"error was raised while loading hook {path!r}:\n{e}")

class _Next:
    __slots__ = ["_frame_stack"]
    def __init__(self, frame_stack: list, /):
        self._frame_stack = frame_stack
    
    def __call__(self, state: StateType, /):
        if self._frame_stack:
            return self._frame_stack.pop()(self, state)
        return state

def execute_action(action: HookAction, state: StateType, /) -> dict:
    return _Next(memory["hooks"][action][:])(state)

# ~~~ runtime .pyi generation and module initialization tool ~~~
import inspect
from types import ModuleType, NoneType, UnionType

class PyiGenerationError(Exception):
    """Base class for all pyi generation errors"""

class RuntimeModulePyi:
    """Runtime module export with hot pyi generation"""

    __slots__ = ["_module", "_names", "_pyi_code", "_python_tab", "_custom_forms"]

    PyiExportedFunctionType = tuple[str, str | None] # [declaration, doc]
    WhatExportType = typing.Literal["function", "class", "type", "variable"]

    def __init__(self, name: str, doc: str | None = None):
        self._module = ModuleType(name, doc)
        self._names = {}
        self._custom_forms = {}
        self._pyi_code = ('"""' + doc + '"""\n') if doc else ""
        self._pyi_code += "from typing import *\n\n" # to avoid late importing need
        self._python_tab = " "*4

    def manual_insert(self, text: str):
        """Function for manually insert text into file"""
        self._pyi_code += text + "\n"

    def manual_export(self, obj, custom_name: str):
        """Function to export obj without generation pyi for it"""
        self._export(obj, custom_name)

    def _generate_type_alias_pyi(self, obj, _skip_self_check: bool = False) -> str:
        pyi_code = ""
        # note: this can cause unexpected automatical type assigment
        if not _skip_self_check and obj in self._custom_forms:
            pyi_code += self._custom_forms[obj]
        elif typing.get_origin(obj) is typing.Literal:
            pyi_code += "Literal[\n" + self._python_tab + f",\n{self._python_tab}".join([f'"{i}"' for i in obj.__args__]) + "\n]"
        elif isinstance(obj, typing.GenericAlias):
            pyi_code = obj.__origin__.__name__ + "["
            for arg in obj.__args__:
                # pyrefly: ignore [unsupported-operation]
                pyi_code += self._names.get(arg.__name__, self._generate_type_alias_pyi(arg))
                pyi_code += ", "
            pyi_code = pyi_code.removesuffix(", ") + "]"
        elif isinstance(obj, type):
            if obj == NoneType:
                pyi_code += "None"
            else:
                pyi_code += self._names.get(obj.__name__, obj.__name__)
        elif isinstance(obj, UnionType):
            for annotation_arg in obj.__args__:
                pyi_code += self._generate_type_alias_pyi(annotation_arg) + " | "
            pyi_code = pyi_code.removesuffix(" | ")
        elif isinstance(obj, NoneType):
            pyi_code += "None"
        else:
            raise PyiGenerationError(f"cannot generate .pyi interface for type: {obj!r}")

        return pyi_code

    def _generate_function_pyi(self, obj, name: str) -> PyiExportedFunctionType:
        sig = inspect.signature(obj)
        pyi_code = "def " + name + "("
        pyi_doc = None
        _pos_only = False
        _kw_only = False
        for varname, parameter in sig.parameters.items():
            if parameter.kind == parameter.VAR_KEYWORD:
                pyi_code += "**"
            elif parameter.kind == parameter.VAR_POSITIONAL:
                pyi_code += "*"
            if _pos_only and parameter.kind != parameter.POSITIONAL_ONLY:
                pyi_code += "/, "
                _pos_only = False
            if not _kw_only and parameter.kind == parameter.KEYWORD_ONLY:
                pyi_code += "*, "
                _kw_only = True
            pyi_code += varname
            if parameter.annotation is not inspect._empty:
                pyi_code += ": " + self._generate_type_alias_pyi(parameter.annotation)
            if parameter.default is not inspect.Parameter.empty:
                pyi_code += " = ..."
            pyi_code += ", "
            if parameter.kind == parameter.POSITIONAL_ONLY:
                _pos_only = True
        pyi_code = pyi_code.removesuffix(", ") + ")"
        if sig.return_annotation is not inspect.Parameter.empty:
            pyi_code += " -> " + self._generate_type_alias_pyi(sig.return_annotation)
        pyi_code += ":"
        if obj.__doc__:
            pyi_doc = '"""' + obj.__doc__ + '"""'
        else:
            pyi_code += " ..."

        return pyi_code, pyi_doc

    def _generate_class_pyi(self, obj, name: str) -> str:
        """
        Generates pyi for classes
        Automatically skips private fields except of popular dunders
        (as analysators need them to be more accurate)
        """
        pyi_code = "class " + name + ":\n"
        if obj.__doc__:
            pyi_code += self._python_tab + '"""' + obj.__doc__ + '"""\n'
        for property_name, property in obj.__dict__.items():
            if property_name in (
                "__init__", "__call__", "__add__", "__sub__", "__mul__", "__truediv__",
                "__floordiv__", "__mod__", "__pow__", "__matmul__", "__radd__", "__rsub__",
                "__rmul__", "__rtruediv__", "__rfloordiv__", "__rmod__", "__rpow__",
                "__rmatmul__", "__iadd__", "__isub__", "__imul__", "__itruediv__",
                "__ifloordiv__", "__imod__", "__ipow__", "__imatmul__", "__neg__",
                "__pos__", "__invert__", "__abs__", "__round__", "__floor__", "__ceil__",
                "__trunc__", "__int__", "__float__", "__complex__", "__eq__", "__ne__",
                "__lt__", "__le__", "__gt__", "__ge__", "__and__", "__or__", "__xor__",
                "__lshift__", "__rshift__", "__rand__", "__ror__", "__rxor__",
                "__rlshift__", "__rrshift__", "__iand__", "__ior__", "__ixor__",
                "__ilshift__", "__irshift__", "__getitem__", "__setitem__", "__delitem__",
                "__iter__", "__next__", "__len__", "__contains__", "__getattribute__",
                "__getattr__", "__setattr__", "__delattr__", "__enter__", "__exit__",
                "__str__", "__repr__", "__format__", "__bytes__", "__hash__", "__bool__",
                "__getstate__", "__setstate__", "__copy__", "__deepcopy__", "__class__",
                "__subclasscheck__", "__instancecheck__", "__index__", "__dir__",
                "__sizeof__", "__getnewargs__"
            ) or not property_name.startswith("_"):
                if isinstance(property, classmethod):
                    pyi_code += self._python_tab + "@classmethod\n"
                    property = property.__func__
                if isinstance(property, staticmethod):
                    pyi_code += self._python_tab + "@staticmethod\n"
                fn_code, fn_doc = self._generate_function_pyi(property, property_name)
                pyi_code += self._python_tab + fn_code + "\n"
                if fn_doc:
                    pyi_code += self._python_tab*2 + fn_doc + "\n"
                pyi_code += "\n"
        return pyi_code

    def _export(self, obj, custom_name: str | None = None, _custom_as_name: bool = False) -> str:
        name = custom_name if custom_name else obj.__name__
        self._names[custom_name if _custom_as_name else obj.__name__] = name
        setattr(self._module, name, obj)
        return name

    def export(self, what: WhatExportType, obj, custom_name: str | None = None):
        """
        Exports `what`
        Raises PyiGenerationError if failed to generate .pyi interface
        """
        if what in ("type", "variable") and not custom_name:
            raise PyiGenerationError("custom_name must be specified when exporting type or variable")
        name = self._export(obj, custom_name, what in ("type", "variable"))
        # pyi generation
        if what == "function":
            fn_code, fn_doc = self._generate_function_pyi(obj, name)
            self._pyi_code += fn_code + "\n"
            if fn_doc:
                self._pyi_code += self._python_tab + fn_doc + "\n"*2
        elif what == "class":
            self._pyi_code += self._generate_class_pyi(obj, name)
        elif what == "type":
            self._pyi_code += name + " = " + self._generate_type_alias_pyi(obj, True) + "\n"*2
            self._custom_forms[obj] = name
        elif what == "variable":
            self._pyi_code += name + ": " + self._generate_type_alias_pyi(type(obj)) + "\n"*2
        else:
            raise PyiGenerationError(f"unknown what: {what!r}")

    def export_function(self, func, custom_name: str | None = None):
        """
        Exports function
        Raises PyiGenerationError if failed to generate .pyi interface
        """
        self.export("function", func, custom_name)

    def export_class(self, cls, custom_name: str | None = None):
        """
        Exports class
        Raises PyiGenerationError if failed to generate .pyi interface
        """
        self.export("class", cls, custom_name)

    def export_type(self, _type, custom_name: str):
        """
        Exports type
        Raises PyiGenerationError if failed to generate .pyi interface
        """
        self.export("type", _type, custom_name)

    def export_variable(self, var, custom_name: str):
        """
        Exports variable
        Raises PyiGenerationError if failed to generate .pyi interface
        """
        self.export("variable", var, custom_name)

    def pyi(self) -> str:
        """Returns generated .pyi code"""
        return self._pyi_code

    def load(self):
        """Loads new module to the python system modules"""
        sys.modules[self._module.__name__] = self._module

# ~~~ making module ~~~
i_plugins = RuntimeModulePyi(
    "imitator_plugins",
"""
convenient plugins API for imitator
~~~ generated by imitator ~~~
"""
)

# export types
i_plugins.export_type(StateType, "StateType")
i_plugins.export_type(HookAction, "HookAction")

# export classes
i_plugins.export_class(TermIO)
i_plugins.export_class(_Next, "NextType")

# export methods
i_plugins.export_function(add_hook)
i_plugins.export_function(hook)
i_plugins.export_function(add_metadata)
i_plugins.export_function(safe_open)
i_plugins.export_function(load_hook_from_file)
i_plugins.export_function(jput)
i_plugins.export_function(jprint)
i_plugins.export_function(set_non_blocking_io)
i_plugins.export_function(set_blocking_io)
i_plugins.export_function(chkkeys, "check_ctrl_c")

# exporting module
i_plugins.load()

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
    """mutates `state`"""
    state["printer_func"] = printer_body
    content = state["content"] # immutable
    state = execute_action("init", state)
    if state["loop"]:
        finish = state["printer_func"](state)
        while not finish:
            state = execute_action("on_end", state)
            if state.get("stop", False):
                break
            state["content"] = content # restore from immutable
            jput("\n") # to separate loops and avoid content overlay
            finish = state["printer_func"](state)
    else:
        state["printer_func"](state)
    execute_action("on_full_end", state)

def interactive(state: dict):
    """mutates `state`"""
    set_non_blocking_io() # to avoid undocumented/unexpected behaviour in plugins
    try:
        state = execute_action("init", state)
        while state["content"]:
            state = execute_action("before", state)
            state = execute_action("instead", state)
            state = execute_action("after", state)
    except KeyboardInterrupt:
        state = execute_action("on_interrupt_occur", state)
    state = execute_action("on_end", state)
    execute_action("on_full_end", state)

# ~~~ default behaviour ~~~
@hook("instead")
def _default_instead(_next: _Next, state: dict):
    state["_val"] = state["content"][0]
    jput(state["_val"])
    state["content"] = state["content"][1:]
    return _next(state)

@hook("after")
def _default_after(_next: _Next, state: dict):
    if state["mode"] == "interactive":
        time.sleep(0.01)
    return _next(state)

# ~~~ main ~~~
def main():
    argparser = argparse.ArgumentParser("imitator", allow_abbrev=False)
    argparser.add_argument(
        "-f", "--file",
        action="store",
        type=str,
        help="file to read text from. required if plugins don't set their own content"
    )
    argparser.add_argument(
        "-m", "--mode",
        action="store",
        type=str,
        choices=[
            "typer",
            "printer",
            "interactive"
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
    argparser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="make output verbose"
    )
    argparser.add_argument(
        "-w", "--wait-before-start",
        action="store",
        type=int,
        help="wait specified seconds before start",
        default=0
    )
    argparser.add_argument(
        "--generate-dev-pyi",
        action="store_true",
        help="generate imitator_plugins.pyi file for development and exit"
    )

    args = argparser.parse_args()

    if args.generate_dev_pyi:
        try:
            with open("imitator_plugins.pyi", "w", encoding="utf-8") as file:
                file.write(i_plugins.pyi())
                exit(0)
        except (OSError, PermissionError) as e:
            fatal(f"cannot write imitator_plugins.pyi due to error: {e}")

    loaded_i = 0

    start_load_time = time.time()
    if args.include:
        import os
        def process(include: str):
            nonlocal loaded_i
            if os.path.isdir(include):
                for inc in os.listdir(include):
                    process(os.path.join(include, inc))
            else:
                load_hook_from_file(include)
                loaded_i += 1
        for include in args.include:
            process(include)
    end_load_time = time.time()
    
    if args.verbose:
        hooks_count = 0
        for hooks in memory["hooks"].values():
            hooks_count += len(hooks)
        print(f"{loaded_i} plugins and {hooks_count} hooks loaded in {(end_load_time - start_load_time)*1000:0.4f} ms")

    # get rid of unused variables
    del start_load_time, end_load_time, loaded_i

    if args.wait_before_start > 0:
        time.sleep(args.wait_before_start)

    state = {
        "loop": args.loop,
        "delay": args.delay,
        "mode": args.mode,
        "content_preview": args.file
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
        if not state["mode"] or state["mode"] == "printer":
            printer(state)
        elif state["mode"] == "interactive":
            interactive(state)
        elif state["mode"] == "typer":
            simulate(state["content"])
        else:
            fatal(f"no such mode: {args.mode!r}")

if __name__ == "__main__":
    main()

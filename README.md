## 📋 Overview

`Imitator` can be used to:
- Simulate human typing.
- Print text character-by-character at a specified delay.
- Extend behavior using hooks (plugins).

It supports both Windows and Unix-like systems and handles keyboard interrupts gracefully.

---

## 🧰 Features

- **Two Modes**:
  - `typer`: Simulates real-time typing.
  - `printer`: Prints characters one by one with configurable delay.

- **Plugin System**:
  - Hooks into different stages of execution (`before`, `instead`, `after`, etc.)
  - Customizable behavior without modifying core code.

- **Cross-platform Support**:
  - Works on Windows and Linux/macOS.
  - Handles raw terminal input properly on each platform.

- **Keyboard Interrupt Handling**:
  - Press `Ctrl+C` to stop execution cleanly.

---

## 🚀 Installation

No installation required — just copy and run the script directly using Python 3.6+:

```bash
python3 imitator.py --help
```

> Note: The script uses standard libraries only, so no extra dependencies are needed.

---

## ⚙️ Usage

### 📄 Sample Text File

Imitator needs a text file to read from. You can use any text file, like this `example.txt`:
```
Hello world!
This is an example of imitator.
Press Ctrl+C to exit early.
```

### Basic Command Syntax

```bash
python3 imitator.py [options]
```

### Running Examples

**Print with Default Settings**

```bash
python3 imitator.py -f example.txt
```

> *Note: this is equivalent to this:*

```bash
python3 imitator.py -f example.txt -m printer
```

**Print with Delay and Endless loop**

```bash
python3 imitator.py -f example.txt -d 0.1 -l
```

**Simulate printing by pressing on any buttons on keyboard**

```bash
python3 imitator.py -f example.txt -m typer
```

**Add Plugin Hook**

```bash
python3 imitator.py -f example.txt -i fancy_print.py -m printer
```

### Options

| Option | Description |
|--------|-------------|
| `-f`, `--file` | Path to the file containing text to print/imitate. |
| `-m`, `--mode` | Mode to run in (`printer`, `typer`, `interactive`). Default: `printer`. |
| `-i`, `--include` | Include a hook plugin or a directory with plugins (can be used multiple times). |
| `-d`, `--delay` | Delay between characters in seconds. Default: `0.01`. |
| `-l`, `--loop` | Loop the text printing infinitely until interrupted. |

---

## 🛠️ Writing Plugins

> ! Plugins working only in `printer` mode right now

Plugins are written as Python files that define hooks using functions decorated with `@hook("action_name")`.

### Imitator python API file

Copy `imitator_plugins.pyi` to your workspace to get language server support (this is not necessary for writing plugins, but highly recommended)

### Hook Actions

| Action | Description |
|--------|-------------|
| `before` | Runs before each character is printed |
| `instead` | Replaces default printing logic |
| `after` | Runs after each character is printed |
| `on_interrupt_occur` | Called when Ctrl+C is pressed |
| `init` | Called once at the start of printing |
| `on_end` | Called at the end of a loop cycle |
| `on_full_end` | Called when all loops are finished |
| `on_start` | Called before anything starts |

### Hook API (see `imitator_plugins.py` for more details)
| Method | Description |
|--------|-------------|
| `hook` | Decorator that register a hook |
| `jput` | Puts character after a previous one |
| `jprint` | Prints string after previous character |
| `safe_open` | Safely open external files from filesystem using Imitator API |
| `load_hook_from_file` | Load dependency hooks from file |
| `add_metadata` | Add hook metadata |
| `add_hook` | Function to register a hook. `hook` uses this internally |

---

### Example Plugin: Change Character Display

> file `fancy_print.py`:
```python
from imitator_plugins import hook, jput

@hook("instead")
def fancy_instead(_next, state):
    char = state["content"][0] # get first symbol from text
    if char == " ":
        char = "*"
    elif char.isalpha():
        char = char.upper()
    state["_val"] = char # saving for other plugins in chain
    jput(char)
    state["content"] = state["content"][1:] # truncate origin text to avoid loop
    return state
```

Run with:

```bash
python3 imitator.py -f example.txt -i fancy_print.py -m printer
```

This will print uppercase letters and spaces as stars.

---

### Example Plugin: Stop on Space

> file `stop_on_space.py`:
```python
from imitator_plugins import hook

@hook("instead")
def stop_on_space(_next, state):
    char = state["content"][0] # get first symbol from text
    if char == " ":
        raise KeyboardInterrupt()
    return _next(state) # give control to next plugin in chain
```

This stops printing when it hits a space.

---

### 🧠 Core Concepts: State Object

All hooks receive a `state` dictionary that contains:
- `"content"`: The text being printed.
- `"delay"`: Time between characters.
- `"loop"`: Whether to loop the content.
- `"mode"`: Running mode (`typer` or `printer`).
- Any custom keys added by plugins.

You can modify this state in hooks, e.g., change delay, stop printing, etc.

---

### 🧪 Advanced Plugin Example

Here's a full plugin that modifies content and adds logging:

> file `advanced_hook.py`:
```python
from imitator_plugins import hook, jprint, jput

@hook("init")
def log_start(_next, state):
    jprint("Starting to print...\n\n") # put the whole string
    return _next(state)

@hook("instead")
def replace_and_log(_next, state):
    char = state["content"][0]
    if char == "a":
        char = "@"
    elif char == "e":
        char = "3"
    jput(char) # put single character
    state["content"] = state["content"][1:]
    return state

@hook("on_full_end")
def log_finished(_next, state):
    # jprint/jput doesn't work here, because
    # on_full_end executes after exit raw terminal mode
    print("\nFinished printing!")
    return _next(state)
```

Run:

```bash
python3 imitator.py -f example.txt -i advanced_hook.py -m printer
```

### Plugin to understand how it works

> file `multiple_instead.py`:
```python
from imitator_plugins import hook, jput

# this plugin will be in the middle of chain
@hook("instead")
def instead1(_next, state):
    jput("1")
    return state # exit after this plugin, to avoid unexpected behaviour

# last loaded plugin
# will be first in plugin chain
@hook("instead")
def instead2(_next, state):
    # here we need to truncate content to avoid loop
    state["_val"] = state["content"][0]
    state["content"] = state["content"][1:]
    jput("2")
    return _next(state) # give control to instead1 function
```

Run:

```bash
python3 imitator.py -f example.txt -i multiple_instead.py -m printer
```

---

## 📝 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 💬 Feedback

Feel free to open an issue or submit a pull request if you'd like to contribute improvements or new features!

--- 

Enjoy using **Imitator** 🚀
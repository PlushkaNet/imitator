from imitator_plugins import hook, jprint, jput, NextType, StateType

@hook("init")
def log_start(_next: NextType, state: StateType):
    jprint("Starting to print...\n\n") # put the whole string
    return _next(state)

@hook("instead")
def replace_and_log(_next: NextType, state: StateType):
    char = state["content"][0]
    if char == "a":
        char = "@"
    elif char == "e":
        char = "3"
    jput(char) # put single character
    state["content"] = state["content"][1:]
    return state # prevent executing default behaviour

@hook("on_full_end")
def log_finished(_next: NextType, state: StateType):
    jprint("\n\nFinished printing!\n")
    return _next(state)
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
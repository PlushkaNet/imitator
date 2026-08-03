from imitator_plugins import hook, NextType, StateType

@hook("instead")
def stop_on_space(_next: NextType, state: StateType):
    char = state["content"][0] # get first symbol from text
    if char == " ":
        raise KeyboardInterrupt()
    return _next(state) # give control to next plugin in chain
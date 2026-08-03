from imitator_plugins import hook, jput, NextType, StateType

# this plugin will be in the middle of chain
@hook("instead")
def instead1(_next: NextType, state: StateType):
    jput("1")
    return state # exit after this plugin, to avoid unexpected behaviour

# last loaded plugin
# will be first in plugin chain
@hook("instead")
def instead2(_next: NextType, state: StateType):
    # here we need to truncate content to avoid loop
    state["_val"] = state["content"][0]
    state["content"] = state["content"][1:]
    jput("2")
    return _next(state) # give control to instead1 function
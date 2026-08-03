from imitator_plugins import hook, jput, NextType, StateType

@hook("instead")
def fancy_instead(_next: NextType, state: StateType):
    char = state["content"][0] # get first symbol from text
    if char == " ":
        char = "*"
    elif char.isalpha():
        char = char.upper()
    state["_val"] = char # saving for other plugins in chain
    jput(char)
    state["content"] = state["content"][1:] # truncate origin text to avoid loop
    return state
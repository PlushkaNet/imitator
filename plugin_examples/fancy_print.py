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
def addTagWrapper(string: str, tag: str, parameters = ""):
    string = "<" + tag + parameters + ">" + string + "</" + tag + ">"
    return string
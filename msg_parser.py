import re


def split_msg(msg):
    """
    splits msg
    example: this: is, some msg -> [this, is, some, msg]
    """
    return re.findall(r"[^\s]+", msg)


def split_msg_raw(msg):
    return msg.split()


def trim_msg(to_trim, full_msg):
    """
    trims full_msg to get just command without following to_trim
    returns empty string when didn't found to_trim
    """
    splited_msg = split_msg(full_msg)
    command = ''

    try:
        if len(splited_msg) > 0 and full_msg.startswith(to_trim):
            to_trim_impl = re.compile(to_trim + r'\W*').findall(full_msg)[0]
            command = full_msg.replace(to_trim_impl, '', 1)
    except: pass

    return command

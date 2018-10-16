import re
import logging


def split_msg(msg):
    """
    splits msg
    example: this: is, some msg -> [this, is, some, msg]
    """
    return re.findall(r"[^\s]+", msg)


def trim_msg(to_trim, full_msg):
    """
    trims full_msg to get just command without following to_trim
    returns empty string when didn't found to_trim
    """
    splited_msg = split_msg(full_msg)
    command = ''

    try:
        if len(splited_msg) > 0 and full_msg.startswith(to_trim):
            to_trim_impl = re.compile(to_trim + r'\s*').findall(full_msg)[0]
            command = full_msg.replace(to_trim_impl, '', 1)
    except Exception as e:
        logging.getLogger(__name__).error(f'exception caught while parsing msg: {type(e).__name__}: {e}')
        return ''

    return command

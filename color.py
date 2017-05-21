colors = {
    "00": "white",
    "01": "black",
    "02": "blue",
    "03": "green",
    "04": "light_red",
    "05": "red",
    "06": "purple",
    "07": "orange",
    "08": "yellow",
    "09": "light_green",
    "10": "cyan",
    "11": "light_cyan",
    "12": "light_blue",
    "13": "pink",
    "14": "gray",
    "15": "light_grey",
}


class color:
    @staticmethod
    def _template(code):
        def _template_impl(str):
            return '\x03' + code + str + '\x0F'

        return _template_impl


def load_colors():
    for code, name in colors.items():
        setattr(color, name, color._template(code))


def unload_colors():
    for code, name in colors.items():
        setattr(color, name, lambda x: x)


def init():
    for code, name in colors.items():
        setattr(color, name, lambda x: x)

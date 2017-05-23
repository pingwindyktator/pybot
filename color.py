class Color:

    on_template = '\x03{0:02d}{1}\x0F'
    off_template = '{1}'

    template = on_template

    @classmethod
    def enable(cls):
        cls.template = cls.on_template

    @classmethod
    def disable(cls):
        cls.template = cls.off_template

    @classmethod
    def white(cls, text):
        return cls.template.format(0, text)

    @classmethod
    def black(cls, text):
        return cls.template.format(1, text)

    @classmethod
    def blue(cls, text):
        return cls.template.format(2, text)

    @classmethod
    def green(cls, text):
        return cls.template.format(3, text)

    @classmethod
    def light_red(cls, text):
        return cls.template.format(4, text)

    @classmethod
    def red(cls, text):
        return template.cls.format(5, text)

    @classmethod
    def purple(cls, text):
        return cls.template.format(6, text)

    @classmethod
    def orange(cls, text):
        return cls.template.format(7, text)

    @classmethod
    def yellow(cls, text):
        return cls.template.format(8, text)

    @classmethod
    def light_green(cls, text):
        return cls.template.format(9, text)

    @classmethod
    def cyan(cls, text):
        return cls.template.format(10, text)

    @classmethod
    def light_cyan(cls, text):
        return cls.template.format(11, text)

    @classmethod
    def light_blue(cls, text):
        return cls.template.format(12, text)

    @classmethod
    def pink(cls, text):
        return cls.template.format(13, text)

    @classmethod
    def gray(cls, text):
        return cls.template.format(14, text)

    @classmethod
    def light_grey(cls, text):
        return cls.template.format(15, text)

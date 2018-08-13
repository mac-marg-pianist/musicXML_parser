class NoteDynamic:
    def __init__(self):
        self.absolute = None
        self.relative = []


class NoteTempo:
    def __init__(self):
        self.absolute = None
        self.relative = []


class NotePedal:
    def __init__(self):
        self.at_start = 0
        self.at_end = 0
        self.refresh = False
        self.refresh_time = 0
        self.cut = False
        self.cut_time = 0
        self.soft = 0
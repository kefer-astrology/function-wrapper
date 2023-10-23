from datetime import datetime
from dateutil.parser import parse

class Actual:
    def __init__(self, content: str="", t: str="time") -> None:
        if t=="time":
            # osetrit cas
            if isinstance(content, str) and len(content) > 0:
                self.value = parse(content)
            elif isinstance(content, datetime):
                self.value = content
            else:
                self.value = datetime.now()
        elif t=="place":
            # osetrit polohu
            if isinstance(content, str):
                self.value = content

    def add_some_time(self, of):
        if isinstance(of, str):
            self.value += parse(of)
        elif isinstance(of, datetime):
            self.value = datetime.combine(self.value, of)

    def move_around_globe(self, city: str="Prague"):
        if isinstance(city, str):
            self.value = city


if __name__ == "__main__":
    # simple test
    a = Actual("15.5.2020")
    
    a = Actual("11/9/1982")

    a = Actual("Prague", t="place")
from datetime import datetime
from dateutil.parser import parse

class Actual:
    def __init__(self, content, t: str="time") -> None:
        if t=="time":
            # osetrit cas
            if isinstance(content, str) and len(content) > 0:
                print(parse(content)) 
            elif isinstance(content, datetime):
                print(content)
            else:
                print(datetime.now())
        elif t=="place":
            # osetrit polohu
            pass




if __name__ == "__main__":
    # simple test
    a = Actual("15.5.2020")
    
    a = Actual("11/9/1982")

    a = Actual("Prague", t="place")
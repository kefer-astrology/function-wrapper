
def change_language(default: str="cz") -> dict:
    if 'cz' in default:
         return {
            "name": "jméno / název: ",
            "loc": "pozice",
            "place": "místo události: ",
            "date": "začátek události: ",
            "display": "zobrazení",
            "time": "přesný čas události: ",
            "new": "nový objekt: ",
            "in_time": "v čase",
            "first": "informace o první události",
            "second": "informace o druhé události",
            "repr": "vyberte typ zobrazení",
            "repr_real": "skutečná pozice objektů",
            "repr_zodi": "zodiakální reprezentace",
            "repr_hous": "tabulky domů",
            "repr_plan": "tabulky planet",
            "repr_moon": "pozice měsíce",
            "run": "spusťte výpočet"
        }
    else:
        return {
            "name": "input a name: ",
            "loc": "location",
            "place": "input an origin palce: ",
            "date": "input initial event date: ",
            "display": "display",
            "time": "input exact time of an event: ",
            "new": "insert a new object: ",
            "in_time": "in time",
            "first": "Start Information",
            "second": "End Information",
            "repr": "select type of computation",
            "repr_real": "object real position",
            "repr_zodi": "zodiac representation",
            "repr_hous": "houses table",
            "repr_plan": "planets table",
            "repr_moon": "moon position",
            "run": "run the computation"
        }

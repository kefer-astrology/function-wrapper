
def change_language(type: str) -> dict:
    if 'cz' in type:
         return {
            "name": "Vložte jméno: ",
            "place": "Vložte místo původu: ",
            "date": "Vložte začátek události (d.m.r h:m): ",
            "new": "Vložte nový objekt: "
        }
    else:
        return {
            "name": "Please input a name: ",
            "place": "Please input palce of birth (origin): ",
            "date": "Please input initial event date (d.m.y h:m): ",
            "new": "Please insert a new object: "
        }

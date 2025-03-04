# Funkční vrstva pro Kefer Astrology

## Popis:

- cache: dočasné soubory pro výpočty
- module: vlastní aplikace
- tests: testování scénářů a funkcionalit
- venv: python prostředí s knihovnami

## Jak to spustit

Funkční vrstva v živém modu:



Příprava prostředí: 

1. create virtual environment: `python -m venv venv`
2. activate virtual environment:
   - Windows: `astro\Scripts\activate`
   - Linux `source ./astro/bin/activate`
3. install libraries:
   - generate requirements `pip-compile --upgrade --strip-extras requirements.in`
   - install from generated req file `pip install -r requirements.txt`
4. run the wrapper ui helper:
   - default `python module` runs on streamlit (`python -m streamlit run module/ui_streamlit.py`)
   - zbytek TBD
   - parameter `python module kivy` (`python module/ui_kivy.py`)
   - command line UI run with `-t` 

## Jak to funguje

Většina práce je provedena modulem [g-battaglia/kerykeion](https://github.com/g-battaglia/kerykeion).


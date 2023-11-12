# AstroSmrk

obyčejný smrkanec letící vesmírem, dokud to neuchopíme.

Adresáře:

- astro: python prostředí s knihovnami
- cache: dočasné soubory pro výpočty
- result: napočítané výsledkové soubory
- smrk: vlastní aplikace
- source: zdrojové soubory pro výpočty
- test: testování scénářů a funkcionalit

## Jak to spustit

1. create virtual environment: `python -m venv astro`
2. activate virtual environment:
   - Windows: `astro\Scripts\activate`
   - Linux `source ./astro/bin/activate`
3. install dependencies: `pip install -r requirements.txt`
4. run it: `python smrk`
   - without parameter call streamlit `python smrk\ui_streamlit.py`
   - `-t` command line mode
   - `-i` image generate

## Jak to funguje

Máme následující úrovně:

- L1: Fyzická pozice planet a objektů z pohledu pozorovatele
- L2: Prostorové uspořádání v kontextu další události
- L3: Porovnání uspořádání více časových okamžiků mezi sebou

Pro L1 je potřeba najít základní grafickou reprezentaci.

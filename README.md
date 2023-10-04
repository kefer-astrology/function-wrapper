# AstroSmrk

obyčejný smrkanec letící vesmírem, dokud to neuchopíme.

Adresáře:

- cache: docasné soubory pro výpočty
- result: napočítané výsledkové soubory
- smrk: vlastní aplikace
- source: zdrojové soubory pro výpočty
- venv: python prostředí s knihovnami

## Jak to spustit

1. create virtual environment: `python -m venv venv`
2. activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux `source ./venv/bin/activate`
3. install dependencies: `pip install -r requirements.txt`
4. run it: `python smrk`

## Jak to funguje

Máme tyto úrovně, které se snažíme pochopit:

- L1: Prostorové uspořádání v určitý časový okamžik
- L2: Prostorové uspořádání v kontextu další události
- L3: Porovnání uspořádání více časových okamžiků mezi sebou

Pro L1 je potřeba najít základní grafickou reprezentaci.

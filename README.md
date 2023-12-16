# AstroSmrk

obyčejný smrkanec letící vesmírem, dokud to neuchopíme.

Adresáře:

- astro: python prostředí s knihovnami
- cache: dočasné soubory pro výpočty
- smrk: vlastní aplikace
- tests: testování scénářů a funkcionalit

## Jak to spustit

Vývojový mod: 

1. create virtual environment: `python -m venv astro`
2. activate virtual environment:
   - Windows: `astro\Scripts\activate`
   - Linux `source ./astro/bin/activate`
3. install dependencies: `pip install -r requirements.txt`
4. run it: `python smrk`
   - streamlit `python - m streamlit run smrk/ui_streamlit.py`
   - kivy `python smrk/ui_kivy.py` 
   - command line UI run with `-t` 

## Jak to funguje

Většina práce je provedena modulem [g-battaglia/kerykeion](https://github.com/g-battaglia/kerykeion).
Grafické rozhraní je obohaceno o některé prvky, aby dokázalo konkurovat aplikaci StarFisher.
# Function layer for Kefer Astrology

## Description (folders):

- cache: temporary files for computation
- module: all the program logic
- scripts: generators for documentation
- tests: scenario and functionality testing
- venv: python environment with libraries

## How to run

Environment preparation: 

1. create virtual environment: `python3 -m venv venv`
2. activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux `source ./venv/bin/activate`
3. install libraries:
   - generate requirements `pip-compile --upgrade --strip-extras requirements.in`
   - install from generated req file `pip3 install -r requirements.txt`
4. run the wrapper ui helper:
   - default `python3 module` runs on streamlit (`python3 -m streamlit run module/ui_streamlit.py`)
   - zbytek TBD
   - parameter `python3 module kivy` (`python3 module/ui_kivy.py`)
   - command line UI run with `-t` 
5. run tests:
   - currently using unittest: `python3 -m unittest`

## How it works

All the heavy lifting is made by a module [g-battaglia/kerykeion](https://github.com/g-battaglia/kerykeion), manipulation layer over [astrorigin/pyswisseph](https://github.com/astrorigin/pyswisseph) (also known as [swiss ephemerides](https://www.astro.com/swisseph/swephinfo_e.htm)), thus the license is inherited (GNU Affero GPL v3.0). Other dependencies are mentioned in the [requirements file](./requirements.in).

For NASA JPL ephemerides we use [skyfielders/python-skyfield](https://github.com/skyfielders/python-skyfield) which comes with MIT license.

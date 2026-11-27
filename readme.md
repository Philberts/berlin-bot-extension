Student project of students from BHT (Berliner Hochschule für technik) 
# Topic: Berlin Bot - An Openstreetmap application for Berlin area
Contributors: Joana Wardenga, Michael Schön, Philipp Meyer, Yesha Raval

## Building the PDF documentation

The PDF is generated from `documentation.md` with [Pandoc](https://pandoc.org/) and a LaTeX engine (XeLaTeX).

### 1. Install the requirements

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install pandoc texlive-xetex texlive-fonts-recommended texlive-latex-extra
```

### 2. Verify the installation
```bash
pandoc --version
xelatex --version
```
Both commands must print a version number.

### 3. Convert the documentation
```bash
pandoc documentation.md -o documentation.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=2.5cm \
  -V mainfont="DejaVu Sans"
```
The result is `documentation.pdf` in the current directory.

Optional flags:
- `--toc` adds a table of contents
- `-N` numbers the headings
- `--highlight-style=tango` sets the code highlighting style

### Alternative: no local installation (Docker)
```bash
docker run --rm -v "$(pwd):/data" pandoc/latex \
  documentation.md -o documentation.pdf \
  --pdf-engine=xelatex -V geometry:margin=2.5cm
```

# -------------------------------
# Installation (Python 3.10+):
python -m venv .venv
.venv\Scripts\activate          (Windows)     source .venv/bin/activate   (Mac / Linux)
pip install -r requirements.txt

# -------------------------------
# Step 1: download the OSM data (Task 1), once per data source
python download_osm.py
python download_osm.py Restaurants        # only one source

# -------------------------------
# Step 2: start the Streamlit app
streamlit run main.py

# -------------------------------
# Files
config.py        data sources and options of the pull-down menus
download_osm.py  OSM download (Overpass via osmnx)
main.py          entry point of the app
core/methods.py  loading, spatial join, indicators, data quality, map, app
datasets/        PLZ and Bezirk polygons, residents, (downloaded) OSM csv files

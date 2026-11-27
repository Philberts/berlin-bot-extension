# Queer Berlin in one Map: Berlin Bot - An Openstreetmap application for the Berlin area
Contributors: Joana Wardenga, Michael Schön, Philipp Meyer, Yesha Raval

Student project of students from BHT (Berliner Hochschule für Technik) 

Berlin Bot maps places across Berlin and includes a simple day planner for LGBTQ+ and cultural venues. Choose a starting location, then build your itinerary by selecting from the five closest unvisited places; distances are straight-line estimates.

# Get started
1. Create venv and install the requirements.
    ```bash
    python -m venv .venv
    source .venv/bin/activate   (Mac / Linux)
    pip install -r requirements.txt
    ```

2. To use the chatbot, either enter an API key in the sidebar or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add a key for your chosen provider. Never commit your API key. The app also works without LLM access.

3. Run the streamlit app:
    ```bash
    streamlit run main.py
    ```

4. Select your LLM-Provider in the sidebar to the left under `Chat assistant (LLM settings)`

The chatbot answers questions about aggregated metrics, not individual venues.

## Building the PDF documentation

The PDF is generated from `documentation.md` with [Pandoc](https://pandoc.org/) and a LaTeX engine (XeLaTeX).

### With no local installation (Docker)
```bash
docker run --rm -v "$(pwd):/data" pandoc/latex \
  documentation.md -o documentation.pdf \
  --pdf-engine=xelatex -V geometry:margin=2.5cm
```

# Files
- config.py        data sources and options of the pull-down menus
- download_osm.py  OSM download (Overpass via osmnx)
- main.py          entry point of the app
- core/methods.py  loading, spatial join, indicators, data quality, map, app, features
- datasets/        PLZ and Bezirk polygons, residents, (downloaded) OSM csv files

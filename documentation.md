# Documentation Berlin-Bot-Extension
**Contributors**: Joana Wardenga, Michael Schön, Philipp Meyer, Yesha Raval

**Students-Project**: Data Science M.Sc., Advanced Software Engineering

This report documents the use case, app changes, results and limitations. The PDF is generated from this Markdown; see the README for the build command.

# Use Case: Queer Berlin in one Map

You are a member of the LGBTQ+ community. You are visiting Berlin for a
weekend, staying for a limited time (e.g. an exchange semester), or living
here permanently. You want to plan a fun day and find out which places
actively welcome LGBTQ+ people.

Online, you mostly find "Top 5" lists that focus on the best-known LGBTQ+
spots. These lists have three shortcomings:

- They mainly cover bars and clubs, and miss other things you enjoy, such as
  museums, theatres and exhibitions.
- They leave out community centres and other places where you can meet
  LGBTQ+ people in a safe environment.
- The information is scattered across many sources, so combining it into a
  single day takes time.

Our Berlin-Bot extension solves this. It shows all of these places on one
map and lets you combine your interests into a complete plan for your day.

# What we changed and why
1. **Added LGBTQ+ places as a data source.** We query OpenStreetMap for LGBTQ+-related tags and keep the tag details and a place category, so users can find places beyond the bars and clubs usually featured in short lists.
2. **Added a Culture data source.** It combines theatres, arts centres, cinemas, museums and galleries, making it easier to include cultural activities when planning a day.
3. **Simplified the data-source menu for this use case.** Playgrounds and charging stations remain in the project but are hidden from the menu, keeping the visible choices more focused on places relevant to the Queer Berlin map.
4. **Applied a subtle pink visual theme.** A light rose-white background, matching sidebar and soft metric cards improve visual consistency and make the Queer Berlin interface feel welcoming without distracting from the map or data.
5. **Made Point map (clusters) the default map view.** The Streamlit app now opens with clustered individual points instead of choropleth areas or a heatmap, highlighting the location of each relevant place immediately.
6. **Added a slim day planner.** Users choose a starting LGBTQ+ or cultural venue and add stops from the five closest unvisited places, recalculated from the latest stop. The itinerary is kept in the current app session and can be restarted.

# Limits of the OSM Data
The amount of LGBTQ+ Tags is not overwhelmingly good.
The cultural facilities are almost entirely missing LGBTQ+ tags. Treating every cultural venue as LGBTQ+-friendly is an assumption, not verified information.
The planner uses straight-line distance, not walking or transit routes, and should be treated as a shortlist rather than a route optimizer.

For “Number per 10,000 residents,” areas with fewer than 500 residents or with missing resident data are shown without a value to avoid unstable rates.

|File	|Objects	|Notes|
|-------|-------|-------|
|osm_lgbtq.csv|	132|	Downloaded 2026-11-27, so it is fresh. Separator is ;.|
|osm_culture.csv|	1,043|	357 galleries, 246 museums, 197 theatres, 140 arts centres, 89 cinemas.|

# Results for the use case
The LGBTQ+ dataset contains 132 places: 54 bars, pubs or clubs and 12 erotic or sauna venues; the other 66 include 13 cafés, 11 community centres, 6 restaurants and bookshops. Its LGBTQ+ tags include 89 “primary,” 37 “welcome” and 4 “only” entries. Of the “welcome” places, 72% are not nightlife venues, supporting daytime plans.

The culture dataset adds 1,043 venues, but only five objects overlap with the LGBTQ+ dataset. The LGBTQ+ dataset itself has only 1 museum, 4 cinemas, 1 library, no theatres and no galleries. Cultural venues therefore broaden the itinerary, but their LGBTQ+ friendliness is an unverified assumption. The day planner is most useful in central areas: 38 places are within 1 km of Nollendorfplatz, while three districts have none.

# Checking two Chatbot Answers against our real data
**Q1**: “Which Berlin district has the highest number of LGBTQ venues per 10,000 residents?”

**Answer**: The district with the highest number of LGBTQ venues per 10,000 residents is Friedrichshain-Kreuzberg, with a value of approximately 1.41 venues per 10,000 residents.

**Human Assessment**: The answer correctly identifies the top district. The data table gives Friedrichshain-Kreuzberg 36 venues and 256,021 residents, which is 1.41 venues per 10,000 residents.

**Q2**: “Which districts have the most cultural facilities per 10,000 residents, and how does data quality affect the conclusion that an area is underserved?”

**Answer**: Mitte leads with 10.02 cultural venues per 10,000 residents, followed by Friedrichshain-Kreuzberg (6.41) and Charlottenburg-Wilmersdorf (5.05). The chatbot cautions that mapping quality varies, noting 23 unnamed objects (2.2%) and 37 PLZ areas without objects (19.5%).

**Human Assessment**: The three values match the district-level data table. The data-quality figures also match the report: 23 unnamed objects (2.2%) and 37 PLZ areas without cultural objects (19.5%). These source-wide figures show possible mapping gaps, but do not by themselves establish that any particular district is underserved.

| Q1 chatbot answer | Q2 chatbot answer |
|:---:|:---:|
| ![Q1 chatbot answer](img/screenshot_Q1.png){ width=100% } | ![Q2 chatbot answer](img/screenshot_Q2.png){ width=100% } |
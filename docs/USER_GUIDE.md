# PECC v1.0.0 user guide

## Start the application

On Windows, double-click `start_app.bat`. On the first run, a local virtual environment is created and Python dependencies are installed. Keep the console window open while PECC is running.

For a manual launch:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Taxonomy and ED assignment

PECC provides taxonomic browsing and scientific-name search. When an exact ED match is unavailable, the application follows the fixed hierarchy:

1. Exact taxon
2. Genus
3. Family
4. Ecological energy proxy
5. Broad taxonomic group

The ecological-proxy selector is shown only after exact, genus, and family matching all fail. Broad-group ED is the final fallback when no suitable ecological proxy is selected/available.

## WoRMS lookup

Local ED matching and calculations do not require internet access. WoRMS taxonomy lookup requires internet access. Resolved taxonomy is cached under the user's local application-data directory as `worms_taxonomy_cache.csv`.

## Energy calculation

PECC multiplies prey wet mass by the assigned ED, then expresses each prey category as a percentage of total estimated prey energy. ED min–max values may also be propagated to conservative sensitivity bounds. These bounds are not confidence intervals.

## Reporting

Retain and report the assignment level used for each prey category. Direct study-specific ED measurements should take precedence when reliable measurements for the study population are available.

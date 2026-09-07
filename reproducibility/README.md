# Figure reproducibility

Run the scripts from this directory (for example, with **Source** in RStudio). The scripts resolve their own directory and use the input files distributed beside them.

## Required R packages

- readxl
- dplyr
- tidyr
- ggplot2
- patchwork

The scripts install missing packages automatically.

## Scripts

### `PECC_Fig2_and_Fig4_Reproducible_Plots.R`
Uses:
- `Fig2_input_leave_one_taxon_out.xlsx`
- `Fig2_input_leave_one_source_out.xlsx`
- `Fig4_input_empirical_application.xlsx`

### `Fig3_External_Evaluation_FINAL.R`
Uses:
- `Fig3_input_external_fallback_only_1082.csv`

Generated plots are written to the local `PECC_Figures_R/` directory.

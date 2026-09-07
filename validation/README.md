# Validation and supplementary data

This directory contains the frozen validation and empirical-application materials corresponding to PECC v1.0.0.

- **S1** — PECC reference library
- **S2** — leave-one-taxon-out validation
- **S3** — leave-one-source-out validation
- **S4** — nested holdout and baseline comparison
- **S5** — independent external evaluation
- **S6** — empirical application
- `validation_reference.json` — compact validation metadata displayed by the application

The aggregate `actual_hierarchy` values in `validation_reference.json` are synchronized with the frozen S2 summary: 127/128 predictions, 99.21875% coverage, MAE 1.0145669291 kJ g⁻¹ WW, RMSE 1.4175327907 kJ g⁻¹ WW, and MAPE 22.0580250574%.

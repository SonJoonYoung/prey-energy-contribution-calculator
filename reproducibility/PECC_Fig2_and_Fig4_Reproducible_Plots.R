# ============================================================
# PECC manuscript figures: Fig. 2, Fig. 3, and Fig. 4
# Run this entire script in RStudio (Source).
#
# Required input files:
#   1) Fig2_input_leave_one_taxon_out.xlsx
#   2) Fig2_input_leave_one_source_out.xlsx
#   3) Fig4_input_empirical_application.xlsx
#
# Output:
#   PECC_Figures_R/
#     Fig2_Observed_vs_Predicted_ED.pdf
#     Fig2_Observed_vs_Predicted_ED.tiff
#     Fig2_Observed_vs_Predicted_ED.png
#     Fig3_CommonSubset_Absolute_Error.pdf
#     Fig3_CommonSubset_Absolute_Error.tiff
#     Fig3_CommonSubset_Absolute_Error.png
#     Fig4_IRI_W_E.pdf
#     Fig4_IRI_W_E.tiff
#     Fig4_IRI_W_E.png
#     Figure_statistics.csv
# ============================================================

# ----------------------------
# 0. Packages
# ----------------------------
required_pkgs <- c("readxl", "dplyr", "tidyr", "ggplot2", "patchwork")

to_install <- required_pkgs[
  !vapply(required_pkgs, requireNamespace, FUN.VALUE = logical(1), quietly = TRUE)
]

if (length(to_install) > 0) {
  install.packages(to_install)
}

library(readxl)
library(dplyr)
library(tidyr)
library(ggplot2)
library(patchwork)

# ----------------------------
# 1. Locate input files
# ----------------------------
# Automatically use the folder containing this .R script.
get_script_dir <- function() {
  frames <- sys.frames()
  ofiles <- vapply(
    frames,
    function(x) {
      if (!is.null(x$ofile)) as.character(x$ofile) else NA_character_
    },
    FUN.VALUE = character(1)
  )
  ofiles <- ofiles[!is.na(ofiles) & nzchar(ofiles)]

  if (length(ofiles) > 0) {
    return(dirname(normalizePath(tail(ofiles, 1), winslash = "/", mustWork = TRUE)))
  }

  # Fallback for interactive use in RStudio
  return(normalizePath(getwd(), winslash = "/", mustWork = TRUE))
}

base_dir <- get_script_dir()

find_input <- function(filename) {
  candidate <- file.path(base_dir, filename)

  if (file.exists(candidate)) {
    return(normalizePath(candidate, winslash = "/", mustWork = TRUE))
  }

  stop(
    paste0(
      "\nRequired input file was not found in the script folder:\n",
      candidate,
      "\n\nPut all three Excel files in the same folder as this R script and run Source again."
    )
  )
}

taxon_file  <- find_input("Fig2_input_leave_one_taxon_out.xlsx")
source_file <- find_input("Fig2_input_leave_one_source_out.xlsx")
case_file   <- find_input("Fig4_input_empirical_application.xlsx")

output_dir <- file.path(base_dir, "PECC_Figures_R")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# ----------------------------
# 2. General plotting theme
# ----------------------------
theme_pecc <- theme_classic(base_size = 11) +
  theme(
    text = element_text(family = "serif"),
    axis.title = element_text(size = 11),
    axis.text = element_text(size = 9),
    axis.line = element_line(linewidth = 0.5),
    axis.ticks = element_line(linewidth = 0.5),
    plot.title = element_text(size = 11, face = "bold", hjust = 0),
    strip.background = element_blank(),
    strip.text = element_text(size = 11),
    legend.position = "bottom",
    legend.title = element_blank()
  )

# ============================================================
# FIG. 2
# Observed vs predicted prey energy density
# ============================================================

taxon <- read_excel(taxon_file, sheet = "Validation_128")

fig2A <- taxon %>%
  filter(!is.na(Selected_pred)) %>%
  transmute(
    Observed = as.numeric(Observed_ED),
    Predicted = as.numeric(Selected_pred),
    Level = case_when(
      Selected_level == "Broad" ~ "Broad group",
      TRUE ~ as.character(Selected_level)
    )
  ) %>%
  mutate(
    Level = factor(
      Level,
      levels = c("Genus", "Family", "Ecological proxy", "Broad group")
    )
  )

source_out <- read_excel(source_file, sheet = "Fallback_Only")

fig2B <- source_out %>%
  filter(
    `Coverage class` == "Predicted",
    !is.na(`Predicted ED`)
  ) %>%
  transmute(
    Observed = as.numeric(`Observed ED`),
    Predicted = as.numeric(`Predicted ED`),
    Level = case_when(
      `Selected level` == "Broad" ~ "Broad group",
      TRUE ~ as.character(`Selected level`)
    )
  ) %>%
  mutate(
    Level = factor(
      Level,
      levels = c("Genus", "Family", "Ecological proxy", "Broad group")
    )
  )

calc_metrics <- function(df) {
  tibble(
    n = nrow(df),
    MAE = mean(abs(df$Predicted - df$Observed)),
    RMSE = sqrt(mean((df$Predicted - df$Observed)^2)),
    MAPE = mean(abs((df$Predicted - df$Observed) / df$Observed)) * 100
  )
}

m2A <- calc_metrics(fig2A)
m2B <- calc_metrics(fig2B)

metric_label <- function(m) {
  sprintf(
    "n = %d\nMAE = %.3f\nRMSE = %.3f\nMAPE = %.2f%%",
    m$n, m$MAE, m$RMSE, m$MAPE
  )
}

shape_vals <- c(
  "Genus" = 21,
  "Family" = 22,
  "Ecological proxy" = 24,
  "Broad group" = 23
)

fill_vals <- c(
  "Genus" = "white",
  "Family" = "grey80",
  "Ecological proxy" = "grey50",
  "Broad group" = "black"
)

make_fig2_panel <- function(df, metrics, panel_title, show_y = TRUE) {
  p <- ggplot(
    df,
    aes(
      x = Observed,
      y = Predicted,
      shape = Level,
      fill = Level
    )
  ) +
    geom_abline(
      slope = 1,
      intercept = 0,
      linetype = "dashed",
      linewidth = 0.55
    ) +
    geom_point(
      size = 2.5,
      colour = "black",
      stroke = 0.65
    ) +
    scale_shape_manual(values = shape_vals, drop = FALSE) +
    scale_fill_manual(values = fill_vals, drop = FALSE) +
    scale_x_continuous(
      limits = c(0, 12),
      breaks = seq(0, 12, 2),
      expand = c(0, 0)
    ) +
    scale_y_continuous(
      limits = c(0, 12),
      breaks = seq(0, 12, 2),
      expand = c(0, 0)
    ) +
    coord_fixed() +
    annotate(
      "label",
      x = 0.45,
      y = 11.55,
      hjust = 0,
      vjust = 1,
      label = metric_label(metrics),
      size = 3.0,
      label.size = 0.25,
      family = "serif"
    ) +
    labs(
      title = panel_title,
      x = expression(Observed~ED~(kJ~g^{-1}~WW)),
      y = if (show_y) expression(Predicted~ED~(kJ~g^{-1}~WW)) else NULL
    ) +
    theme_pecc

  p
}

p2A <- make_fig2_panel(
  fig2A, m2A,
  "(A) Leave-one-taxon-out",
  TRUE
)

p2B <- make_fig2_panel(
  fig2B, m2B,
  "(B) Leave-one-source-out (fallback-only)",
  FALSE
)

fig2 <- p2A + p2B +
  plot_layout(guides = "collect") &
  theme(legend.position = "bottom")

ggsave(
  file.path(output_dir, "Fig2_Observed_vs_Predicted_ED.pdf"),
  fig2,
  width = 180, height = 96, units = "mm"
)

ggsave(
  file.path(output_dir, "Fig2_Observed_vs_Predicted_ED.tiff"),
  fig2,
  width = 180, height = 96, units = "mm",
  dpi = 600, compression = "lzw"
)

ggsave(
  file.path(output_dir, "Fig2_Observed_vs_Predicted_ED.png"),
  fig2,
  width = 180, height = 96, units = "mm",
  dpi = 300
)

# ============================================================
# FIG. 3
# Common subset, paired absolute prediction error
# ============================================================

# IMPORTANT:
# Absolute errors are recalculated from prediction and observed ED.
# This correctly retains valid zero-error predictions, including
# the Family-level prediction for Trisopterus luscus.

common27 <- taxon %>%
  filter(
    !is.na(Genus_pred),
    !is.na(Family_pred),
    !is.na(Proxy_pred),
    !is.na(Broad_pred)
  ) %>%
  transmute(
    Taxon = as.character(Taxon),
    Observed = as.numeric(Observed_ED),
    Genus = abs(as.numeric(Genus_pred) - as.numeric(Observed_ED)),
    Family = abs(as.numeric(Family_pred) - as.numeric(Observed_ED)),
    `Ecological proxy` = abs(as.numeric(Proxy_pred) - as.numeric(Observed_ED)),
    `Broad group` = abs(as.numeric(Broad_pred) - as.numeric(Observed_ED))
  )

stopifnot(nrow(common27) == 27)

fig3_data <- common27 %>%
  pivot_longer(
    cols = c(
      Genus,
      Family,
      `Ecological proxy`,
      `Broad group`
    ),
    names_to = "Level",
    values_to = "Absolute_error"
  ) %>%
  mutate(
    Level = factor(
      Level,
      levels = c(
        "Genus",
        "Family",
        "Ecological proxy",
        "Broad group"
      )
    )
  )

m3 <- fig3_data %>%
  group_by(Level) %>%
  summarise(
    n = n(),
    MAE = mean(Absolute_error),
    RMSE = sqrt(mean(Absolute_error^2)),
    .groups = "drop"
  )

# MAPE is calculated separately from predicted/observed values.
common27_pred_long <- common27 %>%
  select(Taxon, Observed) %>%
  left_join(
    taxon %>%
      filter(Taxon %in% common27$Taxon) %>%
      select(Taxon, Genus_pred, Family_pred, Proxy_pred, Broad_pred),
    by = "Taxon"
  ) %>%
  transmute(
    Taxon,
    Observed,
    Genus = as.numeric(Genus_pred),
    Family = as.numeric(Family_pred),
    `Ecological proxy` = as.numeric(Proxy_pred),
    `Broad group` = as.numeric(Broad_pred)
  ) %>%
  pivot_longer(
    cols = c(Genus, Family, `Ecological proxy`, `Broad group`),
    names_to = "Level",
    values_to = "Predicted"
  ) %>%
  mutate(
    Level = factor(
      Level,
      levels = c("Genus", "Family", "Ecological proxy", "Broad group")
    ),
    APE = abs((Predicted - Observed) / Observed) * 100
  )

m3_mape <- common27_pred_long %>%
  group_by(Level) %>%
  summarise(MAPE = mean(APE), .groups = "drop")

m3 <- left_join(m3, m3_mape, by = "Level")

p3 <- ggplot(
  fig3_data,
  aes(
    x = Level,
    y = Absolute_error,
    group = Taxon
  )
) +
  geom_line(
    colour = "grey80",
    linewidth = 0.35,
    alpha = 0.55
  ) +
  geom_boxplot(
    aes(group = Level),
    width = 0.46,
    outlier.shape = NA,
    fill = "grey92",
    colour = "black",
    linewidth = 0.6
  ) +
  geom_point(
    position = position_jitter(width = 0.03, height = 0),
    shape = 21,
    size = 2.1,
    fill = "white",
    colour = "black",
    stroke = 0.55
  ) +
  scale_x_discrete(
    labels = c(
      "Genus",
      "Family",
      "Ecological\nproxy",
      "Broad\ngroup"
    )
  ) +
  scale_y_continuous(
    limits = c(0, 3),
    breaks = seq(0, 3, 0.5),
    expand = expansion(mult = c(0, 0.02))
  ) +
  labs(
    title = NULL,
    x = NULL,
    y = expression(Absolute~prediction~error~(kJ~g^{-1}~WW))
  ) +
  theme_pecc +
  theme(
    legend.position = "none",
    plot.title = element_blank(),
    axis.text.x = element_text(size = 11),
    plot.margin = margin(5.5, 8, 5.5, 5.5)
  )

ggsave(
  file.path(output_dir, "Fig3_CommonSubset_Absolute_Error.pdf"),
  p3,
  width = 135, height = 100, units = "mm"
)

ggsave(
  file.path(output_dir, "Fig3_CommonSubset_Absolute_Error.tiff"),
  p3,
  width = 135, height = 100, units = "mm",
  dpi = 600, compression = "lzw"
)

ggsave(
  file.path(output_dir, "Fig3_CommonSubset_Absolute_Error.png"),
  p3,
  width = 135, height = 100, units = "mm",
  dpi = 300
)

# ============================================================
# FIG. 4
# %IRI vs %W vs %E empirical application
# ============================================================

case <- read_excel(case_file, sheet = "CaseStudy_Results")

selected_prey <- tibble(
  Predator = c(
    "Trichiurus japonicus", "Trichiurus japonicus",
    "Scomber japonicus", "Scomber japonicus", "Scomber japonicus",
    "Trachurus japonicus", "Trachurus japonicus", "Trachurus japonicus"
  ),
  Prey_group = c(
    "Euphausiacea", "Pisces",
    "Euphausiacea", "Pisces", "Anomura",
    "Pisces", "Amphipoda", "Macrura"
  ),
  Prey_order = c(
    1, 2,
    1, 2, 3,
    1, 2, 3
  )
)

fig4_base <- case %>%
  inner_join(selected_prey, by = c("Predator", "Prey_group")) %>%
  transmute(
    Predator,
    Prey_group,
    Prey_order,
    `%IRI` = as.numeric(`Published_%IRI`),
    `%W` = as.numeric(`Published_%W`),
    `%E` = as.numeric(`Estimated_%E`)
  )

# Preserve prey order separately within each predator.
fig4_long <- fig4_base %>%
  pivot_longer(
    cols = c(`%IRI`, `%W`, `%E`),
    names_to = "Metric",
    values_to = "Contribution"
  ) %>%
  mutate(
    Metric = factor(Metric, levels = c("%IRI", "%W", "%E")),
    Predator_plot = case_when(
      Predator == "Trichiurus japonicus" ~ "italic(Trichiurus~japonicus)",
      Predator == "Scomber japonicus" ~ "italic(Scomber~japonicus)",
      Predator == "Trachurus japonicus" ~ "italic(Trachurus~japonicus)"
    ),
    Predator_plot = factor(
      Predator_plot,
      levels = c(
        "italic(Trichiurus~japonicus)",
        "italic(Scomber~japonicus)",
        "italic(Trachurus~japonicus)"
      )
    ),
    Prey_label = paste(Predator, Prey_order, Prey_group, sep = "___")
  )

# Facet-specific x labels by using a unique factor internally and
# stripping the predator/order prefixes in the displayed label.
prey_levels <- fig4_long %>%
  distinct(Predator, Prey_order, Prey_group, Prey_label) %>%
  arrange(
    factor(
      Predator,
      levels = c(
        "Trichiurus japonicus",
        "Scomber japonicus",
        "Trachurus japonicus"
      )
    ),
    Prey_order
  ) %>%
  pull(Prey_label)

fig4_long$Prey_label <- factor(fig4_long$Prey_label, levels = prey_levels)

clean_prey_label <- function(x) {
  sub("^.*___[0-9]+___", "", x)
}

p4 <- ggplot(
  fig4_long,
  aes(
    x = Prey_label,
    y = Contribution,
    fill = Metric
  )
) +
  geom_col(
    position = position_dodge(width = 0.82),
    width = 0.72,
    colour = "black",
    linewidth = 0.35
  ) +
  facet_wrap(
    ~ Predator_plot,
    scales = "free_x",
    nrow = 1,
    labeller = label_parsed
  ) +
  scale_x_discrete(labels = clean_prey_label) +
  scale_y_continuous(
    limits = c(0, 100),
    breaks = seq(0, 100, 20),
    expand = expansion(mult = c(0, 0.03))
  ) +
  scale_fill_manual(
    values = c(
      "%IRI" = "white",
      "%W" = "grey70",
      "%E" = "black"
    )
  ) +
  labs(
    x = NULL,
    y = "Relative contribution (%)"
  ) +
  theme_pecc +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1),
    panel.spacing = unit(5, "mm")
  )

ggsave(
  file.path(output_dir, "Fig4_IRI_W_E.pdf"),
  p4,
  width = 180, height = 92, units = "mm"
)

ggsave(
  file.path(output_dir, "Fig4_IRI_W_E.tiff"),
  p4,
  width = 180, height = 92, units = "mm",
  dpi = 600, compression = "lzw"
)

ggsave(
  file.path(output_dir, "Fig4_IRI_W_E.png"),
  p4,
  width = 180, height = 92, units = "mm",
  dpi = 300
)

# ============================================================
# 5. Export verification statistics
# ============================================================

stats_out <- bind_rows(
  tibble(
    Figure = "Fig2A",
    Analysis = "Leave-one-taxon-out",
    Level = "Overall PECC hierarchy",
    n = m2A$n,
    MAE = m2A$MAE,
    RMSE = m2A$RMSE,
    MAPE = m2A$MAPE
  ),
  tibble(
    Figure = "Fig2B",
    Analysis = "Leave-one-source-out fallback-only",
    Level = "Overall fallback-only",
    n = m2B$n,
    MAE = m2B$MAE,
    RMSE = m2B$RMSE,
    MAPE = m2B$MAPE
  ),
  m3 %>%
    transmute(
      Figure = "Fig3",
      Analysis = "Common subset",
      Level = as.character(Level),
      n,
      MAE,
      RMSE,
      MAPE
    )
)

write.csv(
  stats_out,
  file.path(output_dir, "Figure_statistics.csv"),
  row.names = FALSE
)

# ----------------------------
# 6. Console checks
# ----------------------------
cat("\n============================================================\n")
cat("PECC figures completed.\n")
cat("Output directory:\n", normalizePath(output_dir, winslash = "/"), "\n\n")

cat("Fig. 2A metrics:\n")
print(m2A)

cat("\nFig. 2B metrics:\n")
print(m2B)

cat("\nFig. 3 common-subset metrics:\n")
print(m3)

cat("\nFig. 4 selected data:\n")
print(
  fig4_base %>%
    arrange(
      factor(
        Predator,
        levels = c(
          "Trichiurus japonicus",
          "Scomber japonicus",
          "Trachurus japonicus"
        )
      ),
      Prey_order
    )
)

cat("\nFiles saved as PDF, 600-dpi TIFF, and 300-dpi PNG.\n")
cat("============================================================\n")

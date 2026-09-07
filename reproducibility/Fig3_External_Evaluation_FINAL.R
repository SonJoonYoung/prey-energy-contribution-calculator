# ============================================================
# PECC Fig. 3 - FINAL VERSION
# Independent external evaluation
# (A) Observed vs predicted ED
# (B) Absolute prediction error by fallback level
# PECC v1.0.0
# ============================================================

packages <- c("ggplot2", "patchwork")
for (p in packages) {
  if (!requireNamespace(p, quietly = TRUE)) {
    install.packages(p, repos = "https://cloud.r-project.org", dependencies = TRUE)
  }
}
library(ggplot2)
library(patchwork)

get_script_dir <- function() {
  frames <- sys.frames()
  ofiles <- vapply(frames, function(x) {
    if (!is.null(x$ofile)) as.character(x$ofile) else NA_character_
  }, FUN.VALUE = character(1))
  ofiles <- ofiles[!is.na(ofiles) & nzchar(ofiles)]
  if (length(ofiles) > 0) {
    return(dirname(normalizePath(tail(ofiles, 1), winslash = "/", mustWork = TRUE)))
  }
  normalizePath(getwd(), winslash = "/", mustWork = TRUE)
}

base_dir <- get_script_dir()
input_file <- file.path(base_dir, "Fig3_input_external_fallback_only_1082.csv")
output_dir <- file.path(base_dir, "PECC_Figures_R")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

if (!file.exists(input_file)) stop(paste0("\nERROR: CSV file not found.\n", input_file, "\n"))

dat <- read.csv(input_file, stringsAsFactors = FALSE, check.names = FALSE)
required_columns <- c("Observed_ED", "Predicted_ED", "Assignment_Level")
missing_columns <- setdiff(required_columns, names(dat))
if (length(missing_columns) > 0) stop(paste0("ERROR: Missing required column(s): ", paste(missing_columns, collapse = ", ")))

dat$Observed_ED <- suppressWarnings(as.numeric(dat$Observed_ED))
dat$Predicted_ED <- suppressWarnings(as.numeric(dat$Predicted_ED))
raw_level <- tolower(trimws(dat$Assignment_Level))
standard_level <- rep(NA_character_, length(raw_level))
standard_level[raw_level == "genus"] <- "Genus"
standard_level[raw_level == "family"] <- "Family"
standard_level[raw_level %in% c("broad", "broad group", "broad taxonomic group", "broad taxonomic-group")] <- "Broad group"
dat$Assignment_Level <- standard_level

dat <- dat[is.finite(dat$Observed_ED) & is.finite(dat$Predicted_ED) & dat$Observed_ED > 0 & !is.na(dat$Assignment_Level), ]
dat$Assignment_Level <- factor(dat$Assignment_Level, levels = c("Genus", "Family", "Broad group"))
dat$Absolute_Error <- abs(dat$Predicted_ED - dat$Observed_ED)
dat$APE <- (dat$Absolute_Error / dat$Observed_ED) * 100

n_total <- nrow(dat)
MAE <- mean(dat$Absolute_Error)
RMSE <- sqrt(mean((dat$Predicted_ED - dat$Observed_ED)^2))
MAPE <- mean(dat$APE)
MdAPE <- median(dat$APE)
Bias <- mean(dat$Predicted_ED - dat$Observed_ED)
cal_model <- lm(Predicted_ED ~ Observed_ED, data = dat)
cal_intercept <- unname(coef(cal_model)[1])
cal_slope <- unname(coef(cal_model)[2])

fallback_levels <- c("Genus", "Family", "Broad group")
level_stats <- do.call(rbind, lapply(fallback_levels, function(level) {
  d <- dat[dat$Assignment_Level == level, ]
  data.frame(
    Assignment_Level = level,
    n = nrow(d),
    MAE = mean(d$Absolute_Error),
    RMSE = sqrt(mean((d$Predicted_ED - d$Observed_ED)^2)),
    MAPE = mean(d$APE),
    MdAPE = median(d$APE)
  )
}))

cat("\nOVERALL EXTERNAL VALIDATION\n")
cat("n       =", n_total, "\n")
cat("MAE     =", sprintf("%.3f", MAE), "kJ g^-1 WW\n")
cat("RMSE    =", sprintf("%.3f", RMSE), "kJ g^-1 WW\n")
cat("MAPE    =", sprintf("%.2f", MAPE), "%\n")
cat("MdAPE   =", sprintf("%.2f", MdAPE), "%\n")
cat("Bias    =", sprintf("%.3f", Bias), "kJ g^-1 WW\n")
cat("Slope   =", sprintf("%.3f", cal_slope), "\n")
print(level_stats, row.names = FALSE)

check_ok <- TRUE
if (n_total != 1082) { warning(paste("Expected n = 1082; observed n =", n_total)); check_ok <- FALSE }
if (abs(MAE - 1.607) > 0.01) { warning(paste("Expected MAE = 1.607; observed MAE =", round(MAE, 3))); check_ok <- FALSE }
if (abs(RMSE - 2.048) > 0.01) { warning(paste("Expected RMSE = 2.048; observed RMSE =", round(RMSE, 3))); check_ok <- FALSE }
if (abs(MdAPE - 32.09) > 0.1) { warning(paste("Expected MdAPE = 32.09%; observed MdAPE =", round(MdAPE, 2))); check_ok <- FALSE }
if (abs(cal_slope - 0.354) > 0.02) { warning(paste("Expected slope = 0.354; observed slope =", round(cal_slope, 3))); check_ok <- FALSE }
if (check_ok) cat("All major statistics match the manuscript values.\n")

theme_pecc <- theme_classic(base_size = 14) +
  theme(
    axis.title = element_text(size = 15),
    axis.text = element_text(size = 12),
    axis.line = element_line(linewidth = 0.7),
    axis.ticks = element_line(linewidth = 0.6),
    plot.title = element_text(size = 15, face = "bold", hjust = 0),
    legend.title = element_blank(),
    legend.text = element_text(size = 11),
    legend.key.width = unit(1.0, "cm"),
    plot.margin = margin(8, 10, 8, 8)
  )

shape_values <- c("Genus" = 1, "Family" = 0, "Broad group" = 18)
xy_max <- ceiling(max(c(dat$Observed_ED, dat$Predicted_ED)))
stat_text <- paste0(
  "n = ", format(n_total, big.mark = ","),
  "\nMAE = ", sprintf("%.3f", MAE),
  "\nMdAPE = ", sprintf("%.2f", MdAPE), "%",
  "\nSlope = ", sprintf("%.3f", cal_slope)
)

pA <- ggplot(dat, aes(x = Observed_ED, y = Predicted_ED, shape = Assignment_Level)) +
  geom_abline(intercept = 0, slope = 1, linetype = "dashed", linewidth = 0.7) +
  geom_smooth(data = dat, aes(x = Observed_ED, y = Predicted_ED), inherit.aes = FALSE,
              method = "lm", formula = y ~ x, se = FALSE, colour = "black", linewidth = 0.9) +
  geom_point(size = 1.30, stroke = 0.55, alpha = 0.32) +
  scale_shape_manual(values = shape_values) +
  scale_x_continuous(breaks = seq(0, xy_max, by = 4)) +
  scale_y_continuous(breaks = seq(0, xy_max, by = 4)) +
  coord_fixed(ratio = 1, xlim = c(0, xy_max), ylim = c(0, xy_max), expand = FALSE) +
  annotate("label", x = xy_max * 0.045, y = xy_max * 0.94, label = stat_text,
           hjust = 0, vjust = 1, size = 3.9, fill = "white", label.size = 0.2) +
  labs(
    title = "(A) Observed vs predicted ED",
    x = expression(paste("Observed ED (kJ ", g^{-1}, " WW)")),
    y = expression(paste("Predicted ED (kJ ", g^{-1}, " WW)")),
    shape = NULL
  ) +
  guides(shape = guide_legend(nrow = 1, byrow = TRUE, override.aes = list(size = 2.3, alpha = 1))) +
  theme_pecc + theme(legend.position = "bottom")

genus_n <- level_stats$n[level_stats$Assignment_Level == "Genus"]
family_n <- level_stats$n[level_stats$Assignment_Level == "Family"]
broad_n <- level_stats$n[level_stats$Assignment_Level == "Broad group"]
x_labels <- c(
  "Genus" = paste0("Genus\n(n = ", genus_n, ")"),
  "Family" = paste0("Family\n(n = ", family_n, ")"),
  "Broad group" = paste0("Broad group\n(n = ", broad_n, ")")
)

pB <- ggplot(dat, aes(x = Assignment_Level, y = Absolute_Error)) +
  geom_boxplot(width = 0.55, fill = "grey95", linewidth = 0.8,
               outlier.shape = 1, outlier.size = 1.2, outlier.stroke = 0.5, outlier.alpha = 0.4) +
  scale_x_discrete(labels = x_labels) +
  scale_y_continuous(breaks = seq(0, 10, by = 2.5), expand = expansion(mult = c(0, 0.03))) +
  labs(
    title = "(B) Absolute prediction error",
    x = NULL,
    y = expression(paste("Absolute prediction error (kJ ", g^{-1}, " WW)"))
  ) +
  theme_pecc +
  theme(legend.position = "none", axis.text.x = element_text(size = 11.5, lineheight = 0.95))

Fig3 <- patchwork::wrap_plots(pA, pB, ncol = 2, widths = c(1.03, 0.97))
print(Fig3)

png_file <- file.path(output_dir, "Fig3_PECC_External_Validation_FINAL.png")
tiff_file <- file.path(output_dir, "Fig3_PECC_External_Validation_FINAL.tiff")
pdf_file <- file.path(output_dir, "Fig3_PECC_External_Validation_FINAL.pdf")

ggplot2::ggsave(filename = png_file, plot = Fig3, width = 11.8, height = 5.9, units = "in", dpi = 600, bg = "white")
ggplot2::ggsave(filename = tiff_file, plot = Fig3, width = 11.8, height = 5.9, units = "in", dpi = 600, compression = "lzw", bg = "white")
ggplot2::ggsave(filename = pdf_file, plot = Fig3, width = 11.8, height = 5.9, units = "in", bg = "white")

cat("\nFIG. 3 COMPLETED SUCCESSFULLY\n")
cat("PNG:\n", png_file, "\n\n")
cat("TIFF:\n", tiff_file, "\n\n")
cat("PDF:\n", pdf_file, "\n")

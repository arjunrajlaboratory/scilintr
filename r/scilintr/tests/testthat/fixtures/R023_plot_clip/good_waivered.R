library(ggplot2)
results <- read.csv("recursive_probe_summary.csv")
# ANALYSIS_OK[plot-transform]: pmax(., 0) used only on a log-axis sub-panel;
# the signed-range panel below shows the full distribution including negatives.
results$ari_display <- pmax(results$ari, 0)
ggplot(results, aes(node, ari_display)) + geom_col() + scale_y_log10()
ggplot(results, aes(node, ari)) + geom_col() + geom_hline(yintercept = 0)

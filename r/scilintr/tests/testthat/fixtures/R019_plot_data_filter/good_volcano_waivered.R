library(ggplot2)
de_results <- read.csv("de_results.csv")
FDR_THRESHOLD <- 0.05
# ANALYSIS_OK[plot-filter]: label only significant genes on the volcano;
# does NOT affect DE results.
plot_df <- de_results[de_results$padj < FDR_THRESHOLD, ]
ggplot(plot_df, aes(log2FC, -log10(padj))) + geom_point()

# EXPECTED: R019 at line 5

library(ggplot2)
de_results <- read.csv("de_results.csv")
plot_df <- de_results[de_results$padj < 0.05, ]
ggplot(plot_df, aes(log2FC, -log10(padj))) + geom_point()

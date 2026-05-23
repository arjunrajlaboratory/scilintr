# EXPECTED: R023 at line 5

library(ggplot2)
results <- read.csv("recursive_probe_summary.csv")
results$ari_display <- pmax(results$ari, 0)
ggplot(results, aes(node, ari_display)) + geom_col()

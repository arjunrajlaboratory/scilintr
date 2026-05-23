# EXPECTED: R023 at line 6

library(ggplot2)
results <- read.csv("recursive_probe_summary.csv")
ggplot(results, aes(node, ari)) + geom_col() +
  ylim(0, NA)

library(ggplot2)
results <- read.csv("recursive_probe_summary.csv")
ggplot(results, aes(node, ari)) +
  geom_col() +
  geom_hline(yintercept = 0)

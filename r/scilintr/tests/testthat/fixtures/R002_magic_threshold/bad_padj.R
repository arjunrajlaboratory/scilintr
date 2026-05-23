# EXPECTED: R002 at line 4

de_results <- read.csv("de_results.csv")
sig <- de_results[de_results$padj < 0.05, ]

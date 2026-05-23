FDR_THRESHOLD <- 0.05
de_results <- read.csv("de_results.csv")
sig <- de_results[de_results$padj < FDR_THRESHOLD, ]

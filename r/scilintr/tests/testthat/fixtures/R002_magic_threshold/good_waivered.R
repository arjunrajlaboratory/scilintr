# ANALYSIS_OK[threshold]: FDR = 0.05 pre-declared in METHODS.md §3.1;
# sensitivity table includes 0.01 and 0.10 cuts.
de_results <- read.csv("de_results.csv")
sig <- de_results[de_results$padj < 0.05, ]

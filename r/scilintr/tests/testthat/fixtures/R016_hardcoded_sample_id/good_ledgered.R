metadata <- read.csv("metadata.csv")
# ANALYSIS_OK[sample-exclusion]: S17 and S23 failed predeclared sequencing QC;
# see build/dropped_samples.tsv for the ledger.
exclude <- c("S17", "S23")
metadata <- metadata[!metadata$sample_id %in% exclude, ]

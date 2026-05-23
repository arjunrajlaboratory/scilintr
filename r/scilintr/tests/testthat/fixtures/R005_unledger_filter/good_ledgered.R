metadata <- read.csv("metadata.csv")
# ANALYSIS_OK[sample-filter]: drop samples that failed predeclared sequencing QC;
# count recorded below.
n_before <- nrow(metadata)
metadata <- metadata[metadata$qc_pass, ]
write.csv(
  data.frame(n_dropped = n_before - nrow(metadata)),
  "build/dropped_samples.tsv"
)

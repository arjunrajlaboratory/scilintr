# ANALYSIS_OK[join]: one-to-one by construction — batch_info has exactly
# one row per sample, asserted upstream by validate_batch_info.R.
library(dplyr)
metadata <- read.csv("metadata.csv")
batch_info <- read.csv("batch_info.csv")
metadata <- left_join(metadata, batch_info, by = "sample_id")

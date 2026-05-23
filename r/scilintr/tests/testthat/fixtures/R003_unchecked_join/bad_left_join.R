# EXPECTED: R003 at line 6

library(dplyr)
metadata <- read.csv("metadata.csv")
batch_info <- read.csv("batch_info.csv")
metadata <- left_join(metadata, batch_info, by = "sample_id")

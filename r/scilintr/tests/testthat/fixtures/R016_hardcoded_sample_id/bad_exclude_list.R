# EXPECTED: R016 at line 4

metadata <- read.csv("metadata.csv")
exclude <- c("S17", "S23")
metadata <- metadata[!metadata$sample_id %in% exclude, ]

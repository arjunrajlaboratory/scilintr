# EXPECTED: R005 at line 4

metadata <- read.csv("metadata.csv")
metadata <- metadata[metadata$qc_pass, ]

# EXPECTED: R004 at line 5

counts <- read.csv("counts.csv")
metadata <- read.csv("metadata.csv")
metadata <- metadata[1:ncol(counts), ]
expr_values <- as.matrix(counts)
labels <- metadata$condition

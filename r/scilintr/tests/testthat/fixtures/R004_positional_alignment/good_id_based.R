counts <- read.csv("counts.csv")
metadata <- read.csv("metadata.csv")
counts <- counts[, metadata$sample_id]
stopifnot(identical(colnames(counts), metadata$sample_id))
labels <- metadata$condition

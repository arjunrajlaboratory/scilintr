counts <- read.csv("counts.csv")
metadata <- read.csv("metadata.csv")
# ANALYSIS_OK[id-alignment]: metadata$sample_id is asserted to match counts
# column order on the line above; positional truncation is safe.
stopifnot(identical(metadata$sample_id[seq_len(ncol(counts))], colnames(counts)))
metadata <- metadata[seq_len(ncol(counts)), ]

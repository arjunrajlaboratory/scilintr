# ANALYSIS_OK[positional-access]: column index 4 is the treatment column;
# asserted at runtime before use.
TREATMENT_COL_INDEX <- 4L
metadata <- read.csv("metadata.csv")
stopifnot(colnames(metadata)[TREATMENT_COL_INDEX] == "treatment")
condition <- metadata[, TREATMENT_COL_INDEX]

source("_lib.R")

# ANALYSIS_OK[shadow-overwrite]: this script uses the legacy v1 form of
# score_module (median rather than mean); intentional override documented
# in NOTES.md.
score_module <- function(x) {
  median(x, na.rm = TRUE)
}

result <- score_module(rnorm(10))

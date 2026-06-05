# EXPECTED: R030 at line 9

# Cohort loader: on read failure the handler quietly superassigns the
# shared `cohort` object to NULL, so every downstream stage runs on
# nothing instead of the analysis stopping.
tryCatch(
  cohort <- load_cohort(path),
  error = function(e) {
    cohort <<- NULL
  }
)

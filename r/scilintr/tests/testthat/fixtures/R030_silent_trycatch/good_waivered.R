# ANALYSIS_OK[tryCatch-NA]: Firth separation expected on ~0.5% of candidates;
# NAs logged to build/firth_failures.tsv and excluded with explicit count
# reported in the supplement.
fit <- tryCatch(
  firth_fit(x, y),
  error = function(e) {
    log_failure(id, conditionMessage(e))
    NA_real_
  }
)

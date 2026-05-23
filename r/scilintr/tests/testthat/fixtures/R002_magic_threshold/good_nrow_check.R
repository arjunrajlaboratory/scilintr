# `nrow(df) > 0` is a non-empty check, not a threshold.
ensure_nonempty <- function(df) {
  stopifnot(nrow(df) > 0)
  df
}

count_positive <- function(x) {
  sum(x > 0)
}

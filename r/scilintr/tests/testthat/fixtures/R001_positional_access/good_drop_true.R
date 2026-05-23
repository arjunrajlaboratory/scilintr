# `drop = TRUE` is a named-arg literal, not a positional index.
slice_one <- function(df, j) {
  df[, j, drop = TRUE]
}

score_module <- function(x) {
  mean(x, na.rm = TRUE)
}

bind_rows_fill <- function(lst) {
  do.call(rbind, lst)
}

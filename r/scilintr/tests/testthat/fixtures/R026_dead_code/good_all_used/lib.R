score_burden <- function(panel) {
  rowSums(panel, na.rm = TRUE)
}

score_mean <- function(panel) {
  rowMeans(panel, na.rm = TRUE)
}

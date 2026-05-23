# EXPECTED: R026 at line 4

# never called from any consumer
score_burden <- function(panel) {
  rowSums(panel, na.rm = TRUE)
}

score_used <- function(panel) {
  rowMeans(panel, na.rm = TRUE)
}

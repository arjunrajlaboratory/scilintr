# STAGE: library

# ANALYSIS_OK[sample-specific-default]: 191L is the A191 patient ID; this
# script is the A191-only diagnostic harness, not generic library code.
axis_seed_split_a191 <- function(X, k = 2L) {
  set.seed(191L)
  kmeans(X, centers = k)$cluster
}

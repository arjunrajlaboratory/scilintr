# EXPECTED: R021 at line 5
# STAGE: library

axis_seed_split <- function(X, k = 2L) {
  set.seed(191L)
  kmeans(X, centers = k)$cluster
}

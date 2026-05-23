# STAGE: library

axis_seed_split <- function(X, k = 2L, seed = NULL) {
  if (!is.null(seed)) set.seed(seed)
  kmeans(X, centers = k)$cluster
}

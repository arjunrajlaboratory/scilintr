# EXPECTED: R022 at line 5

per_bootstrap <- function(idx, X) {
  # set.seed inside fn body pollutes RNG state when called from mclapply
  set.seed(191L)
  X_b <- X[sample(nrow(X), replace = TRUE), ]
  kmeans(X_b, centers = 3L)$cluster
}

cl_list <- parallel::mclapply(1:100, per_bootstrap, X = X)

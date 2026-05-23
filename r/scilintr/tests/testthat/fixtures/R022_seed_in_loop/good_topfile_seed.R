set.seed(20260523L)

per_bootstrap <- function(idx, X) {
  X_b <- X[sample(nrow(X), replace = TRUE), ]
  kmeans(X_b, centers = 3L)$cluster
}

cl_list <- parallel::mclapply(1:100, per_bootstrap, X = X)

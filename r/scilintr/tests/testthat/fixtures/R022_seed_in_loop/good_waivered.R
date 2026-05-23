# ANALYSIS_OK[seed-inside-fn]: reseeding on every call is intentional —
# this is the per-task entry point for reproducible parallel work; the
# outer RNG stream is pinned via L'Ecuyer streams in the dispatcher.
per_bootstrap <- function(idx, X, seed) {
  set.seed(seed)
  X_b <- X[sample(nrow(X), replace = TRUE), ]
  kmeans(X_b, centers = 3L)$cluster
}

cl_list <- parallel::mclapply(1:100, function(i) {
  per_bootstrap(i, X, seed = 1000L + i)
})

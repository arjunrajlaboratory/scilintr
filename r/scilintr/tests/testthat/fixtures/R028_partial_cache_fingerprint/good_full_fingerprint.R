compute_loglik <- function(N, Y, idx_e) {
  cache_key <- digest::digest(list(N = N, Y = Y, idx_e = idx_e))
  cache_path <- sprintf("build/loglik_%s.rds", cache_key)
  if (file.exists(cache_path)) return(readRDS(cache_path))
  ll <- sum(dbinom(Y, N, prob = 0.5, log = TRUE))
  saveRDS(ll, cache_path)
  ll
}

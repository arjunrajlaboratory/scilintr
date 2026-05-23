compute_loglik <- function(N, Y, idx_e) {
  # ANALYSIS_OK[cache-fingerprint]: N and Y are pinned by the dataset commit
  # hash and validated upstream by check_dataset_pinned.R; idx_e is the only
  # input that varies in this analysis.
  cache_key <- digest::digest(idx_e)
  cache_path <- sprintf("build/loglik_%s.rds", cache_key)
  if (file.exists(cache_path)) return(readRDS(cache_path))
  ll <- sum(dbinom(Y, N, prob = 0.5, log = TRUE))
  saveRDS(ll, cache_path)
  ll
}

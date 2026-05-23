# ANALYSIS_OK[multi-definition]: v2 with full parameter count; canonical
# for current pipeline. See NOTES.md for the v1 vs v2 history.
delta_bic <- function(loglik_a, loglik_b, k_a, k_b, n) {
  -2 * (loglik_a - loglik_b) + (k_a - k_b) * log(n)
}

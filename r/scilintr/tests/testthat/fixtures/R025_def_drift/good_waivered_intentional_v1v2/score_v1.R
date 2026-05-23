# ANALYSIS_OK[multi-definition]: legacy v1 implementation kept for the
# historical reproduction script; not used by the current pipeline.
delta_bic <- function(loglik_a, loglik_b, n_loci) {
  -2 * (loglik_a - loglik_b) + log(n_loci)
}

delta_bic <- function(loglik_a, loglik_b, k_a, k_b, n) {
  -2 * (loglik_a - loglik_b) + (k_a - k_b) * log(n)
}

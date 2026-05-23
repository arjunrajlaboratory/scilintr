# EXPECTED: R025 at line 4

# different signature from lib_bic.R::delta_bic — silent drift
delta_bic <- function(loglik_a, loglik_b, n_loci) {
  -2 * (loglik_a - loglik_b) + log(n_loci)
}

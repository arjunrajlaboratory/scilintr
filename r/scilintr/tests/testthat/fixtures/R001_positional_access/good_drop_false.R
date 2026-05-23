# column index is the SYMBOL `cols`; the FALSE in `drop = FALSE`
# is a named-arg literal, not a positional index — rule must not fire.
subset_seldat <- function(seldat, keep_snp) {
  list(
    N = seldat$N[, keep_snp, drop = FALSE],
    Y = seldat$Y[, keep_snp, drop = FALSE]
  )
}

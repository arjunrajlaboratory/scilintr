# ANALYSIS_OK[composite-weights]: weights pre-declared in decisions_pre_run.md
# before any labelled scoring run; sensitivity in composite_weight_sensitivity.R
# shows ranking unchanged for weights in [w_i +/- 0.1].
score_module <- function(a, b, c, d) {
  0.30 * a + 0.40 * b + 0.20 * c + 0.10 * d
}

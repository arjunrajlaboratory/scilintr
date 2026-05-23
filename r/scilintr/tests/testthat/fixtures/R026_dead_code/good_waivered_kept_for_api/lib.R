# ANALYSIS_OK[unused-fn]: kept exported for downstream-package API stability;
# scheduled for removal in v0.2.0 once consumers migrate to score_v2().
score_legacy <- function(panel) {
  rowSums(panel, na.rm = TRUE)
}

score_v2 <- function(panel) {
  rowMeans(panel, na.rm = TRUE)
}

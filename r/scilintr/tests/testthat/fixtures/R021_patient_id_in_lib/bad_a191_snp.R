# EXPECTED: R021 at line 5
# STAGE: library

pc_summarize_ranking <- function(panel) {
  anchor <- "X17.76565019G.A"
  panel[panel$snp_id != anchor, ]
}

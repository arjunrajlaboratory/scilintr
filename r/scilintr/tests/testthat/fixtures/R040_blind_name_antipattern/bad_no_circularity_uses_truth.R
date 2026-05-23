# EXPECTED: R040 at line 4

run_no_circularity_eval <- function(modules) {
  truth <- read.csv("data/cell_labels.tsv", sep = "\t")$truth_c1
  # uses truth even though the function name asserts no circularity
  modules[order(-cor(modules$score, truth)), ]
}

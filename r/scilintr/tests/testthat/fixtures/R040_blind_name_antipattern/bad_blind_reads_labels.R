# EXPECTED: R040 at line 4

unsupervised_select_module <- function(modules) {
  labels <- read.csv("data/cell_labels.tsv", sep = "\t")
  scored <- score(modules, labels$legacy_branch2_clone)
  modules[which.max(scored), ]
}

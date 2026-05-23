# EXPECTED: R034 at line 8
# STAGE: selection

scores <- read.csv("module_scores.csv")
labels <- read.csv("data/cell_labels.tsv", sep = "\t")
out <- data.frame(
  cell_id = scores$cell_id,
  score = scores$score,
  ari = scores$ari,
  legacy_branch2_clone = labels$legacy_branch2_clone
)
write.csv(out, "selected_calls.csv", row.names = FALSE)

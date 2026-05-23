# STAGE: selection

scores <- read.csv("module_scores.csv")
out <- data.frame(
  cell_id = scores$cell_id,
  score = scores$score,
  ari = scores$ari
)
write.csv(out, "selected_calls.csv", row.names = FALSE)

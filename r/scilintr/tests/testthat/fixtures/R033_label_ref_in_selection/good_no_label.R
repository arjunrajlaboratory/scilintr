# STAGE: selection

df <- read.csv("module_scores.csv")
top <- df[df$score > 0.5, c("cell_id", "score")]
write.csv(top, "selected_calls.csv", row.names = FALSE)

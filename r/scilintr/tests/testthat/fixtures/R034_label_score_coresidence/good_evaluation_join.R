# STAGE: evaluation

selected <- read.csv("selected_calls.csv")
labels <- read.csv("data/cell_labels.tsv", sep = "\t")
# ANALYSIS_OK[label-co-residence]: evaluation-stage CSV; selection-stage output
# was selected_calls.csv (labels-free); see HANDOFF.md.
out <- merge(selected, labels, by = "cell_id")
write.csv(out, "selected_calls_evaluated.csv", row.names = FALSE)

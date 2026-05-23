# STAGE: evaluation

selected <- read.csv("selected_calls.csv")
labels <- read.csv("data/cell_labels.tsv", sep = "\t")
joined <- merge(selected, labels, by = "cell_id")
write.csv(joined, "selected_calls_evaluated.csv", row.names = FALSE)

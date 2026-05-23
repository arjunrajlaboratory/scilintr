# EXPECTED: R033 at line 5
# STAGE: selection

df <- read.csv("module_scores.csv")
truth <- df$legacy_branch2_clone
top <- df[df$score > 0.5, ]

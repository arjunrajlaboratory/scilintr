# EXPECTED: R033 at line 6
# STAGE: selection

library(dplyr)
df <- read.csv("module_scores.csv")
selected <- df %>% filter(score > 0.5) %>% pull(cell_type)

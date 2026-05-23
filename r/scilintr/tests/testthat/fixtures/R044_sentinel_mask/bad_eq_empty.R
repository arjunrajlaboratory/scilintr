# EXPECTED: R044 at line 4

df <- read.csv("treatment_table.csv")
missing_mask <- df$treatment == ""
df <- df[!missing_mask, ]

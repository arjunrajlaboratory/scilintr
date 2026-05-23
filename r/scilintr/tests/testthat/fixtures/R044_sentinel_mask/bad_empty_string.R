# EXPECTED: R044 at line 4

df <- read.csv("treatment_table.csv")
keep <- df$treatment != ""
df_clean <- df[keep, ]

df <- read.csv("treatment_table.csv", na.strings = c("", "NA"))
keep <- !is.na(df$treatment)
df_clean <- df[keep, ]

# Non-zero comparison on numerics is out of scope.
nonzero <- counts != 0
expr <- counts[nonzero]

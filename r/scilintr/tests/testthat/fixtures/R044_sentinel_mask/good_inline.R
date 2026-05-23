# Inline subscript form is R005 territory, not R044.
# Don't flag this here.
df <- read.csv("treatment_table.csv")
df_clean <- df[df$treatment != "", ]

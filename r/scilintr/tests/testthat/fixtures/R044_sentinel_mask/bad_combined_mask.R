# EXPECTED: R044 at line 4

df <- read.csv("samples.csv")
keep <- (df$treatment != "") & (df$batch != "")
df_clean <- df[keep, ]

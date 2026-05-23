# EXPECTED: R032 at line 5

library(dplyr)
df <- read.csv("scored_snps.csv")
ranked <- arrange(df, desc(score), desc(truth_c1))

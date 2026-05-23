# EXPECTED: R032 at line 4

df <- read.csv("scored_snps.csv")
ranked <- df[order(-df$score, -df$is_gt_label), ]

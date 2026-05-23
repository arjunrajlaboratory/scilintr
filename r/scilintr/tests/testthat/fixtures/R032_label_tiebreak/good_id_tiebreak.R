df <- read.csv("scored_snps.csv")
# deterministic lexicographic tie-break on snp_id; is_gt NOT in the key
ranked <- df[order(-df$score, df$snp_id), ]

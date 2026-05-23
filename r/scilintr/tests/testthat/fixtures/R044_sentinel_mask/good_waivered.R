# ANALYSIS_OK[sentinel-mask]: upstream CSV uses "" for missing treatment
# label — documented in DATASET_INFO.md; downstream code is sentinel-aware.
df <- read.csv("treatment_table.csv")
keep <- df$treatment != ""
df_clean <- df[keep, ]

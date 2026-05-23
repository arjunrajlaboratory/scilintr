df <- read.csv("data.csv")
# ANALYSIS_OK[missingness]: drop samples missing the design variable only;
# count logged below.
n_dropped <- sum(is.na(df$treatment))
df <- df[!is.na(df$treatment), ]
message("R006: dropped ", n_dropped, " samples missing treatment")

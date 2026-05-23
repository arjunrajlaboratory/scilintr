# EXPECTED: R036 at line 5
# STAGE: selection

sweep <- read.csv("output/gt17_band_sweep.csv")
BAND <- sweep[which.max(sweep$gt_recall), c("lo", "hi")]
panel <- panel_source[panel_source$vaf > BAND$lo & panel_source$vaf < BAND$hi, ]

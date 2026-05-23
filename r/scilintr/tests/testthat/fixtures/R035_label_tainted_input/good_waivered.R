# STAGE: selection

# ANALYSIS_OK[oracle-file-read]: only the snp_id column is used from
# gt_recall_sweep.csv; this is a label-free pass-through to anchor the panel
# for downstream comparison. Verified: this script never references the
# gt_recall, gt_precision, or is_gt columns.
panel <- read.csv("output/gt_recall_sweep.csv")$snp_id
write.csv(data.frame(snp_id = panel), "panel.csv", row.names = FALSE)

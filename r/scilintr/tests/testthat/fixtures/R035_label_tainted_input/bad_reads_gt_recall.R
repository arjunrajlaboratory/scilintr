# EXPECTED: R035 at line 5
# STAGE: selection

# label-tainted input even if only the snp_id column is used
sweep <- read.csv("output/gt17_band_sweep.csv")
panel <- sweep$snp_id[1:30]
write.csv(data.frame(snp_id = panel), "panel.csv", row.names = FALSE)

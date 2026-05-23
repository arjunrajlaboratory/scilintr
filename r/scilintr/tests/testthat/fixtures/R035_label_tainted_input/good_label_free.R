# STAGE: selection

panel_source <- read.csv("output/band_022_036_unfiltered.csv")
panel <- panel_source$snp_id[1:30]
write.csv(data.frame(snp_id = panel), "panel.csv", row.names = FALSE)

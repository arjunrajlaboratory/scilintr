expr <- as.matrix(read.csv("expr.csv", row.names = 1))
# ANALYSIS_OK[batch-correction]: remove sequencing batch only;
# treatment is NOT included as a covariate.
expr_corrected <- sva::ComBat(dat = expr, batch = metadata$batch)

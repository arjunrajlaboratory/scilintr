# EXPECTED: R014 at line 4

expr <- as.matrix(read.csv("expr.csv", row.names = 1))
expr_corrected <- sva::ComBat(dat = expr, batch = metadata$batch)

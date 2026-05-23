# EXPECTED: R014 at line 4

expr <- as.matrix(read.csv("expr.csv", row.names = 1))
expr_resid <- residualize(expr, covariates = metadata[, c("library_prep", "rin")])

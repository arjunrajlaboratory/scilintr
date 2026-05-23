# STAGE: selection

expr <- as.matrix(read.csv("expr.csv", row.names = 1))
genes <- select_high_variance_genes(expr, n = 2000)
pca <- prcomp(expr[genes, ])

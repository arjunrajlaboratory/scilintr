# EXPECTED: R012 at line 6
# STAGE: selection

expr <- as.matrix(read.csv("expr.csv", row.names = 1))
metadata <- read.csv("metadata.csv")
genes <- select_genes_associated_with(metadata$treatment)
pca <- prcomp(expr[genes, ])

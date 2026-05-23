# EXPECTED: R011 at line 4

X <- as.matrix(read.csv("expr.csv", row.names = 1))
emb <- uwot::umap(X)

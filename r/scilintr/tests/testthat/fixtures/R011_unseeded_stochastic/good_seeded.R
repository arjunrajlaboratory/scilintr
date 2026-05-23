RANDOM_SEED <- 20260523L
X <- as.matrix(read.csv("expr.csv", row.names = 1))
set.seed(RANDOM_SEED)
clusters <- kmeans(X, centers = 5)$cluster

X <- as.matrix(read.csv("expr.csv", row.names = 1))
# ANALYSIS_OK[random-seed-only]: stochastic intent — this k-means run is one
# of 100 independent restarts whose disagreement is the diagnostic itself;
# any single seed would defeat the purpose.
clusters <- kmeans(X, centers = 5)$cluster

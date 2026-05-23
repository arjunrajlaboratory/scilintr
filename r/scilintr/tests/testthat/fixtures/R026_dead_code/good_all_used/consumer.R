source("lib.R")
X <- matrix(rnorm(10), nrow = 2)
a <- score_burden(X)
b <- score_mean(X)

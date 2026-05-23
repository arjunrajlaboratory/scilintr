# EXPECTED: R017 at line 4

df <- read.csv("data.csv")
fit <- suppressWarnings(glm(y ~ x, family = binomial, data = df))

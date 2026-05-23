df <- read.csv("data.csv")
# ANALYSIS_OK[warning-suppression]: suppress known glm.fit "fitted probabilities
# numerically 0 or 1" warning for this specific call; data warnings are not
# suppressed elsewhere.
fit <- suppressWarnings(glm(y ~ x, family = binomial, data = df))

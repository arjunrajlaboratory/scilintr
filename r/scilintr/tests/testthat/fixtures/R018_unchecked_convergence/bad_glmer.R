# EXPECTED: R018 at line 5

library(lme4)
df <- read.csv("data.csv")
fit <- glmer(y ~ x1 + (1 | subject), data = df, family = binomial)
beta <- fixef(fit)

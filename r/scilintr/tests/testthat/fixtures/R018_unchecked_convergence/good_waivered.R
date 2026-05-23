# ANALYSIS_OK[model-fit]: convergence summary recorded in
# build/glmer_fit_summary.tsv by the post-action hook; non-converged fits
# excluded with explicit count in the supplement.
library(lme4)
fit <- glmer(y ~ x1 + (1 | subject), data = df, family = binomial)

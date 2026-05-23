# ANALYSIS_OK[synthetic-test-fixture]: random Poisson counts for unit test;
# seed pinned; never used as analysis input.
set.seed(20260523)
counts <- matrix(rpois(200 * 12, 10), nrow = 200)

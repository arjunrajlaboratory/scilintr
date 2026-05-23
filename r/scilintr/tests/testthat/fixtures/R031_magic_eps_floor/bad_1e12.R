# EXPECTED: R031 at line 4

# 1e-12 floor used to be hit by rate_burden values on {0, 1/k, 2/k, ...}
bic_score <- function(x) log(pmax(x, 1e-12))

# EXPECTED: R030 at line 4

# Firth-GLM convergence failures silently mapped to NULL
fit <- tryCatch(firth_fit(x, y), error = function(e) NULL)

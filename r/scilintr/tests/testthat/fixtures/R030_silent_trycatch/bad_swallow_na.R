# EXPECTED: R030 at line 4

# Wilcoxon failures silently mapped to NA_real_
p <- tryCatch(wilcox.test(a, b)$p.value, error = function(e) NA_real_)

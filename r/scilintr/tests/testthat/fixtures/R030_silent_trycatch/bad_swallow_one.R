# EXPECTED: R030 at line 4

# fisher.test FEXACT-workspace failures silently mapped to p=1
p <- tryCatch(fisher.test(tbl)$p.value, error = function(e) 1)

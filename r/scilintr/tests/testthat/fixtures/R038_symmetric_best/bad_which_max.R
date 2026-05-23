# EXPECTED: R038 at line 4

# pick side with higher c1 after labels are joined
best_side <- c("target", "rest")[which.max(c(target_c1, rest_c1))]

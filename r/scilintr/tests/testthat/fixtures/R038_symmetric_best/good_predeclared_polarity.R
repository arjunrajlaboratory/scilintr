# ANALYSIS_OK[symmetric-best]: side polarity pre-declared via mean panel alt-bit;
# orientation frozen before label join.
target_side <- if (mean(panel_target_alt) < mean(panel_rest_alt)) "target" else "rest"
best_metric <- if (target_side == "target") target_side_ari else rest_side_ari

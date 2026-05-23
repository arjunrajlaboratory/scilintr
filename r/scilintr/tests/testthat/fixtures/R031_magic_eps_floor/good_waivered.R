# ANALYSIS_OK[log-floor]: 1e-12 is below the discretisation grid;
# floor sensitivity tested in bimodality_varfloor_sanity.R, ranking
# unchanged for floor in [1e-15, 1e-9].
bic_score <- function(x) log(pmax(x, 1e-12))

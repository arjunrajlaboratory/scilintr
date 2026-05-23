SCORE_WEIGHTS <- yaml::read_yaml("config/lineage_like_weights.yml")$weights

score_module <- function(terms) {
  sum(SCORE_WEIGHTS * terms)
}

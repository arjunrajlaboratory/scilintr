# STAGE: library

# ANALYSIS_OK[smuggled-default]: top_modules = 25L is the pre-declared primary
# value; recorded in decisions_pre_run.md; CSV outputs carry an is_primary flag.
rank_modules <- function(modules, top_modules = 25L) {
  modules[order(-modules$score), ][seq_len(top_modules), ]
}

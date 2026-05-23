# EXPECTED: R024 at line 4
# STAGE: library

rank_modules <- function(modules, top_modules = 25L) {
  modules[order(-modules$score), ][seq_len(top_modules), ]
}

# STAGE: library

rank_modules <- function(modules, top_modules) {
  modules[order(-modules$score), ][seq_len(top_modules), ]
}

collapse_branch <- function(panel, mode = c("lowest", "highest", "mut_type")) {
  mode <- match.arg(mode)
  if (mode == "lowest")  return(rowSums(panel == 0L))
  if (mode == "highest") return(rowSums(panel == 1L))
  stop("unreachable")
}

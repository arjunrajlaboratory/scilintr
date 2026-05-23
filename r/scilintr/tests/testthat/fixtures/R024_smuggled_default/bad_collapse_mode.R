# EXPECTED: R024 at line 4
# STAGE: library

collapse_branch <- function(panel, mode = "lowest") {
  if (mode == "lowest") rowSums(panel == 0L) else rowSums(panel == 1L)
}

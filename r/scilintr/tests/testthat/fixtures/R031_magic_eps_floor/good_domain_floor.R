N_CELLS <- 200L
score <- function(x) log(pmax(x, 1 / (2 * N_CELLS)))

# EXPECTED: R020 at line 6

source("_lib.R")

# silently shadows _lib.R::score_module
score_module <- function(x) {
  median(x, na.rm = TRUE)
}

result <- score_module(rnorm(10))

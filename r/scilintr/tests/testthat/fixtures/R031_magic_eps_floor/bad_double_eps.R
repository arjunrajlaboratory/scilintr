# EXPECTED: R031 at line 4

# .Machine$double.eps floor is not justified by data discretisation
score <- function(x) log(pmax(x, .Machine$double.eps))

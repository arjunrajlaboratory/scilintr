# EXPECTED: R009 at line 5

get_results <- function() {
  cache <- "build/results.rds"
  if (file.exists(cache)) return(readRDS(cache))
  results <- compute_results()
  saveRDS(results, cache)
  results
}

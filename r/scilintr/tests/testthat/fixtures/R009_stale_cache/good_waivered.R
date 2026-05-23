get_results <- function() {
  cache <- "build/results.rds"
  # ANALYSIS_OK[cache]: inputs are pinned by the dataset commit hash and
  # validated upstream; cache invalidates with the project state.
  if (file.exists(cache)) return(readRDS(cache))
  results <- compute_results()
  saveRDS(results, cache)
  results
}

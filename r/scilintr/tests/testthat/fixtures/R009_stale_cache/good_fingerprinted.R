get_results <- function(inputs) {
  cache <- "build/results.rds"
  fingerprint <- paste(vapply(inputs, tools::md5sum, character(1)),
                       collapse = "")
  if (file.exists(cache)) {
    cached <- readRDS(cache)
    if (identical(cached$fingerprint, fingerprint)) return(cached$results)
  }
  results <- compute_results(inputs)
  saveRDS(list(results = results, fingerprint = fingerprint), cache)
  results
}

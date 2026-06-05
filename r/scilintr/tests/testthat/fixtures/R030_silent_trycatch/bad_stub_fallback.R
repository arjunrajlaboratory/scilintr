# EXPECTED: R030 at line 9

# If the optional fast scorer can't be loaded, the handler swaps in a
# no-op stub that returns NULL for every record -- scoring silently
# becomes a no-op instead of falling back to the reference scorer.
tryCatch(
  score_fn <- load_fast_scorer(),
  error = function(e) {
    score_fn <<- function(...) NULL
  }
)

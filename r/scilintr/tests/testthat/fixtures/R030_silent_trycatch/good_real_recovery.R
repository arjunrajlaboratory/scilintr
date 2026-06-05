# On a transient read failure, fall back to the last good cached copy
# -- a real recovered value, not a degraded placeholder -- and log it.
# The block does work and returns a genuine object, so it must not fire.
counts <- tryCatch(
  read_counts(path),
  error = function(e) {
    warning("falling back to cached counts: ", conditionMessage(e))
    readRDS(cache_path)
  }
)

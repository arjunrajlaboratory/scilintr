# No file.exists() check at all — let read.csv() raise naturally.
load_panel <- function(path) {
  read.csv(path)
}

# Negated file.exists() but NOT returning NULL — this is fine.
ensure_dir <- function(path) {
  if (!file.exists(path)) {
    dir.create(path, recursive = TRUE)
  }
  invisible(path)
}

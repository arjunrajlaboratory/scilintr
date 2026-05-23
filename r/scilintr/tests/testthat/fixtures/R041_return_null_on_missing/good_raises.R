load_panel <- function(path) {
  if (!file.exists(path)) {
    stop("panel file not found: ", path)
  }
  read.csv(path)
}

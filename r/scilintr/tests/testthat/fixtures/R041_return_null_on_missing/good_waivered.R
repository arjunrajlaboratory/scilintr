load_panel <- function(path) {
  # ANALYSIS_OK[optional-input]: panel is an optional annotation; callers
  # check is.null(panel) explicitly and use the unannotated branch.
  if (!file.exists(path)) {
    return(NULL)
  }
  read.csv(path)
}

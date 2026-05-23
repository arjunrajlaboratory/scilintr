#' Load scilintr configuration from a project root.
#'
#' Looks for `.scilintr.yml`, `analysis_labels.yml`, and
#' `analysis_identifiers.yml` at the project root.
#'
#' @keywords internal
load_config <- function(root = ".") {
  paths <- list(
    main         = file.path(root, ".scilintr.yml"),
    labels       = file.path(root, "analysis_labels.yml"),
    identifiers  = file.path(root, "analysis_identifiers.yml")
  )
  out <- lapply(paths, function(p) {
    if (file.exists(p)) yaml::read_yaml(p) else NULL
  })
  out
}

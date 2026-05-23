#' Flag stochastic function calls (kmeans, umap, Rtsne, tsne) that lack a
#' nearby `set.seed(...)` call.
#'
#' v1 heuristic: if the file contains *any* `set.seed(...)` call, suppress all
#' findings for that file. Otherwise emit one Lint per known stochastic call.
#' The waiver comment `ANALYSIS_OK[random-seed-only]` is handled by the
#' orchestrator's `apply_waivers`, not here.
#'
#' Known stochastic call names: `kmeans`, `umap` (covers `uwot::umap` —
#' SYMBOL_FUNCTION_CALL matches the bare function name even under `pkg::`),
#' `Rtsne`, `tsne`.
#'
#' @keywords internal
unseeded_stochastic_linter <- function() {
  stochastic_names <- c("kmeans", "umap", "Rtsne", "tsne")
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    filename <- source_expression$filename
    if (is.null(filename) || !nzchar(filename) || !file.exists(filename)) {
      return(list())
    }
    file_text <- paste(readLines(filename, warn = FALSE), collapse = "\n")
    if (grepl("set\\.seed\\s*\\(", file_text)) return(list())

    predicate <- paste0(
      "text()='", stochastic_names, "'", collapse = " or "
    )
    calls <- xml2::xml_find_all(
      xml,
      paste0("//SYMBOL_FUNCTION_CALL[", predicate, "]")
    )

    lapply(as.list(calls), function(node) {
      lintr::Lint(
        filename    = filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R011: stochastic call `", xml2::xml_text(node),
          "(...)` without `set.seed(...)` in this file — ",
          "results will not be reproducible."
        )
      )
    })
  })
}

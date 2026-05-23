#' Flag join/merge calls without a follow-up cardinality assertion.
#'
#' Detects calls to `left_join`, `right_join`, `inner_join`, `full_join`,
#' `anti_join`, `semi_join`, or `merge`. If the file contains a row-count
#' or duplicate-key check (`stopifnot(...)`, `anyDuplicated`, or a
#' `validate = ...` argument), the rule treats the joins as covered and
#' emits nothing. Otherwise, every join call is flagged.
#'
#' V1 is intentionally file-level and trigger-happy. Upstream assertions
#' in another file are handled by the orchestrator's `ANALYSIS_OK[join]`
#' waiver layer, not here.
#'
#' @keywords internal
unchecked_join_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    file_text <- paste(
      readLines(source_expression$filename, warn = FALSE),
      collapse = "\n"
    )
    if (grepl("stopifnot\\s*\\(|validate\\s*=|anyDuplicated", file_text)) {
      return(list())
    }

    nodes <- xml2::xml_find_all(
      xml,
      paste0(
        "//SYMBOL_FUNCTION_CALL[",
        "text()='left_join' or text()='right_join' or ",
        "text()='inner_join' or text()='full_join' or ",
        "text()='anti_join' or text()='semi_join' or ",
        "text()='merge'",
        "]"
      )
    )

    lapply(as.list(nodes), function(n) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(n, "line1")),
        type        = "warning",
        message     = paste(
          "R003: join/merge without a follow-up cardinality check --",
          "add `stopifnot(nrow(x) == n_before)` or",
          "`stopifnot(!anyDuplicated(key))` after the join."
        )
      )
    })
  })
}

# R017 -- warning / message suppression ---------------------------------

#' Flag `suppressWarnings(...)` and `suppressMessages(...)` calls.
#'
#' Blanket suppression hides diagnostics that often signal real
#' problems (e.g. `glm.fit` non-convergence, NA coercion, dropped
#' factor levels). Narrow, justified suppressions should be paired
#' with an `ANALYSIS_OK[warning-suppression]` waiver comment; the
#' orchestrator's waiver layer handles silencing those.
#'
#' v1 scope: only the `suppress*` functions. `options(warn = -1)`
#' is deferred.
#'
#' @keywords internal
warning_suppression_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[",
        "text()='suppressWarnings' or text()='suppressMessages']]"
      )
    )

    lapply(as.list(calls), function(node) {
      fn <- xml2::xml_find_first(node, "expr[1]/SYMBOL_FUNCTION_CALL")
      fn_name <- xml2::xml_text(fn)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R017: ", fn_name, "() hides diagnostics that often signal real ",
          "problems; scope narrowly and justify with an ",
          "ANALYSIS_OK[warning-suppression] waiver."
        )
      )
    })
  })
}

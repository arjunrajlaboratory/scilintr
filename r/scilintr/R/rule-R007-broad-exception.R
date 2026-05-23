# R007 -- broad exception handling: try(..., silent = TRUE) -------------

#' Flag `try(..., silent = TRUE)`.
#'
#' `try(expr, silent = TRUE)` swallows errors without logging or
#' rethrowing — the caller continues with a `try-error` object that
#' often gets coerced or ignored downstream. v1 detects exactly this
#' pattern; broader fallback heuristics are deferred.
#'
#' This is distinct from R030, which targets `tryCatch(..., error =
#' function(e) <literal>)` handlers.
#'
#' @keywords internal
broad_exception_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='try']",
        " and SYMBOL_SUB[text()='silent']",
        "/following-sibling::expr[1]/NUM_CONST[text()='TRUE']]"
      )
    )

    lapply(as.list(calls), function(node) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste(
          "R007: try(..., silent = TRUE) swallows errors —",
          "log explicitly or use tryCatch with a real handler."
        )
      )
    })
  })
}

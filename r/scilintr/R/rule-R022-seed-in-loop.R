# R022 -- set.seed() inside a function body ----------------------------

#' Flag `set.seed(...)` calls inside a function literal.
#'
#' v1 heuristic per `analysis_lint_strategy.md` R022: a `set.seed()`
#' that is not at script top level -- i.e. nested inside any enclosing
#' `function(...) <body>` -- pollutes the global RNG state when the
#' function is invoked from a loop or parallel worker. The reproducibility
#' contract belongs to the dispatcher (top-level seed or L'Ecuyer streams),
#' not the per-task callee.
#'
#' Detection: any `<SYMBOL_FUNCTION_CALL>set.seed</SYMBOL_FUNCTION_CALL>`
#' that has an ancestor `<expr>` containing a `<FUNCTION>` child.
#'
#' @keywords internal
seed_in_loop_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml, "//SYMBOL_FUNCTION_CALL[text()='set.seed']"
    )

    bad <- lapply(as.list(calls), function(node) {
      enclosing_fn <- xml2::xml_find_first(node, "ancestor::expr[FUNCTION]")
      if (length(enclosing_fn) == 0L || is.na(xml2::xml_name(enclosing_fn))) {
        return(NULL)
      }
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste(
          "R022: set.seed() inside a function body pollutes global RNG",
          "state when called in a loop or parallel worker -- seed once at",
          "top level, or use L'Ecuyer streams for parallel reproducibility."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

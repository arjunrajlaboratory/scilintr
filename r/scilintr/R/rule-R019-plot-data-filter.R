# R019 -- plotting code that changes data ---------------------------------

#' Flag filtering assignments whose LHS name starts with `plot_`.
#'
#' Pattern:
#' ```
#'   plot_df <- de_results[de_results$padj < 0.05, ]
#'   plot_df <- df %>% filter(...)
#' ```
#'
#' Visual filtering (subsetting for a single chart) silently mutates the
#' analysis population if the same `plot_df` is later treated as the DE
#' result. We flag the assignment; a `# ANALYSIS_OK[plot-filter]:` waiver
#' on a neighbouring line suppresses elsewhere via the shared waiver layer.
#'
#' @keywords internal
plot_data_filter_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    xpath <- paste0(
      "//expr[",
      "  LEFT_ASSIGN",
      "  and starts-with(expr[1]/SYMBOL/text(), 'plot_')",
      "  and expr[2][",
      "    .//OP-LEFT-BRACKET",
      "    or .//SYMBOL_FUNCTION_CALL[text()='filter' or text()='subset']",
      "  ]",
      "]"
    )

    hits <- xml2::xml_find_all(xml, xpath)
    lints <- list()
    for (node in as.list(hits)) {
      lhs <- xml2::xml_find_first(node, "./expr[1]/SYMBOL")
      lhs_name <- if (length(lhs)) xml2::xml_text(lhs) else "plot_*"
      lints[[length(lints) + 1L]] <- lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R019: '", lhs_name,
          "' filters/subsets data for plotting -- ",
          "visual filtering can silently change the analysis population. ",
          "If intentional, add `# ANALYSIS_OK[plot-filter]: <reason>`."
        )
      )
    }
    lints
  })
}

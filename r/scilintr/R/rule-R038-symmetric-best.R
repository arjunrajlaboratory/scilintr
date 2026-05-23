#' R038 -- Symmetric "best of either side" reporting
#'
#' Flag `pmax(...)`, `max(...)`, or `which.max(c(...))` whose argument
#' subtree contains two or more SYMBOLs whose names look like
#' side/polarity labels (`target_*`, `rest_*`, `left_*`, `right_*`,
#' `*_aligned`, `*_complement`, `*_c1`, `*_side`).
#'
#' Picking "the better of two label-named sides" after labels are joined
#' is a hidden test-multiplication / label-aware fishing pattern. Fix is
#' to pre-declare which side is the target side via a label-independent
#' rule and freeze the orientation before label joins
#' (see `analysis_lint_strategy.md` section 38).
#'
#' V1 is file-local and intentionally conservative: it fires only when
#' the heuristic finds at least two side-label-shaped SYMBOLs inside the
#' max-like call's subtree. Pre-declared if/else polarity (no
#' pmax/max/which.max) does not match.
#'
#' @keywords internal
symmetric_best_linter <- function() {
  side_pattern <- paste0(
    "(^|_)(target|rest|left|right|aligned|complement)(_|$)",
    "|(^|_)(c1|side)(_|$)"
  )

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//SYMBOL_FUNCTION_CALL[",
        "text()='pmax' or text()='max' or text()='which.max'",
        "]"
      )
    )

    bad <- lapply(as.list(calls), function(fn_node) {
      call_expr <- xml2::xml_parent(xml2::xml_parent(fn_node))
      symbols <- xml2::xml_find_all(call_expr, ".//SYMBOL")
      names <- xml2::xml_text(symbols)
      side_hits <- names[grepl(side_pattern, names, perl = TRUE)]
      if (length(unique(side_hits)) < 2L) return(NULL)
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(fn_node, "line1")),
        type        = "warning",
        message     = paste0(
          "R038: symmetric `",
          xml2::xml_text(fn_node),
          "` over side-labeled variables (",
          paste(unique(side_hits), collapse = ", "),
          ") -- pre-declare side polarity via a label-independent rule",
          " before the label join, or add an ANALYSIS_OK[symmetric-best]",
          " waiver."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

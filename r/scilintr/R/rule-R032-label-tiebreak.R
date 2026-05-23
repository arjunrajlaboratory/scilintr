# R032 -- tie-break on a label / ground-truth column --------------------

#' Flag `order(...)` / `arrange(...)` calls whose secondary sort key
#' references a label-named column (e.g. `is_gt_label`, `truth_c1`,
#' `is_target`). A secondary key drives ranking *for ties* — if the
#' tie-breaker is the answer key, the ranking is leaky.
#'
#' Detection:
#'  * Call is `order(...)` or `arrange(...)`.
#'  * Walk all arguments after the first; if any of their descendant
#'    SYMBOLs match the label-name regex below, flag.
#'  * Match is case-insensitive and matches names containing
#'    `is_gt`, `gt_label`, `truth`, `is_target`, or trailing `_label`.
#'
#' @keywords internal
label_tiebreak_linter <- function() {
  label_re <- "(?i)(is_gt|gt_label|truth|is_target|_label$)"

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[",
        "  text()='order' or text()='arrange'",
        "]]"
      )
    )

    bad <- lapply(as.list(calls), function(ce) {
      # Argument <expr> children: position 1 is the function name,
      # positions >=2 are the actual call args.
      arg_exprs <- xml2::xml_find_all(ce, "expr")
      if (length(arg_exprs) < 3L) return(NULL)

      fname <- xml2::xml_text(
        xml2::xml_find_first(arg_exprs[[1L]], "SYMBOL_FUNCTION_CALL")
      )
      # arrange()'s first arg is the data frame -> tie-breakers start
      # at position 3 of arg_exprs. order()'s first arg is the primary
      # sort key -> tie-breakers start at position 3 as well.
      tiebreak_start <- 3L
      if (length(arg_exprs) < tiebreak_start) return(NULL)
      tiebreakers <- arg_exprs[tiebreak_start:length(arg_exprs)]

      flagged <- FALSE
      for (tb in tiebreakers) {
        syms <- xml2::xml_find_all(tb, ".//SYMBOL | .//SYMBOL_FORMALS")
        sym_names <- xml2::xml_text(syms)
        if (any(grepl(label_re, sym_names, perl = TRUE))) {
          flagged <- TRUE
          break
        }
      }
      if (!flagged) return(NULL)

      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(ce, "line1")),
        type        = "warning",
        message     = paste0(
          "R032: secondary sort key in `", fname,
          "(...)` references a label/ground-truth column — tie-breakers",
          " decide ranking for ties; use a leak-free key",
          " (independent prior rank, lexicographic ID, or seeded random)."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

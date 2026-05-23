# R031 -- magic epsilon floors inside log / log1p / log10 / log2 -------

#' Flag `log(pmax(x, <tiny-literal>))` and friends.
#'
#' A floor like `1e-12` or `.Machine$double.eps` (~2.2e-16) inside a
#' `pmax()` immediately before `log()` is a numerical-stability
#' landmine when the floor sits below the data's natural
#' discretisation grid. The floor then dominates the score and
#' confuses ranking comparisons. Use a domain-motivated floor (e.g.
#' half the smallest non-zero increment), not a generic safety
#' constant.
#'
#' Detection:
#'  * Outer call is `log` / `log1p` / `log10` / `log2`.
#'  * Inner call is `pmax` / `pmax.int`.
#'  * Second `pmax` argument is either a `NUM_CONST` with numeric
#'    value `< 1e-6`, or the expression `.Machine$double.eps`.
#'  * `pmax(x, 1 / (2 * N))` and similar compound expressions are not
#'    flagged — the second argument is not a single literal.
#'
#' @keywords internal
magic_eps_floor_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # log(...)/log1p(...)/log10(...)/log2(...) whose sole argument expr
    # is a pmax(...)/pmax.int(...) call. Anchor on the pmax expr.
    pmax_exprs <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[",
        "  expr[1]/SYMBOL_FUNCTION_CALL[",
        "    text()='log' or text()='log1p' or text()='log10' or text()='log2'",
        "  ]",
        "]/expr[expr[1]/SYMBOL_FUNCTION_CALL[",
        "  text()='pmax' or text()='pmax.int'",
        "]]"
      )
    )

    bad <- lapply(as.list(pmax_exprs), function(pe) {
      # Children <expr> of the pmax call (skip the function-name expr
      # in position 1). Arg 1 = data, arg 2 = floor.
      arg_exprs <- xml2::xml_find_all(pe, "expr")
      if (length(arg_exprs) < 3L) return(NULL)
      floor_expr <- arg_exprs[[3L]]
      kids <- xml2::xml_children(floor_expr)

      is_magic <- FALSE
      if (length(kids) == 1L && xml2::xml_name(kids[[1]]) == "NUM_CONST") {
        val <- suppressWarnings(as.numeric(xml2::xml_text(kids[[1]])))
        if (!is.na(val) && val < 1e-6) is_magic <- TRUE
      } else if (length(kids) == 3L &&
                 xml2::xml_name(kids[[2]]) == "OP-DOLLAR") {
        lhs <- xml2::xml_find_first(kids[[1]], "SYMBOL")
        rhs <- kids[[3]]
        if (length(lhs) > 0L &&
            xml2::xml_text(lhs) == ".Machine" &&
            xml2::xml_name(rhs) == "SYMBOL" &&
            xml2::xml_text(rhs) == "double.eps") {
          is_magic <- TRUE
        }
      }
      if (!is_magic) return(NULL)

      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(pe, "line1")),
        type        = "warning",
        message     = paste(
          "R031: log(pmax(x, <tiny constant>)) — use a domain-motivated",
          "floor (e.g. half the smallest non-zero increment),",
          "not a generic numerical-safety epsilon."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

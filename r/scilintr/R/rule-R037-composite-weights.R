# R037 -- composite scores with literal weights and >= 3 terms --------

#' Flag `w1*x1 + w2*x2 + w3*x3 + ...` composite scores with literal weights.
#'
#' Hand-tuned weights on composite scores are a provenance landmine:
#' each literal weight is a degree of freedom, and three or more
#' compounded weights make post-hoc tuning trivially deniable. We flag
#' any `+`-joined expression with three-or-more terms where at least
#' one term has an explicit numeric coefficient (`<NUM_CONST> * <expr>`)
#' or is itself a bare `<NUM_CONST>`.
#'
#' Allowed via `ANALYSIS_OK[composite-weights]` waiver that cites the
#' weight-provenance record and a sensitivity check.
#'
#' Detection:
#'  * Find each top-level `+` `<expr>` (i.e., an `<expr>` whose direct
#'    children include `OP-PLUS` but whose parent does NOT, so we only
#'    anchor on the outermost `+` in a chain).
#'  * Recurse through the `+` tree to enumerate plus-joined leaf terms.
#'  * If `>= 3` leaves and at least one leaf is `<NUM_CONST> * <expr>`
#'    or a literal `<NUM_CONST>`, flag the outer expression.
#'
#' @keywords internal
composite_weights_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # `<expr>` nodes that have a direct OP-PLUS child but whose parent
    # `<expr>` does NOT — i.e., the outermost node of any `+` chain.
    plus_exprs <- xml2::xml_find_all(
      xml,
      "//expr[OP-PLUS and not(parent::expr/OP-PLUS)]"
    )

    # Walk a `+` tree, returning the list of leaf <expr> nodes (the
    # plus-joined terms). A node is a leaf when it lacks a direct
    # OP-PLUS child.
    collect_plus_terms <- function(node) {
      plus <- xml2::xml_find_first(node, "OP-PLUS")
      if (is.na(plus)) return(list(node))
      kids <- xml2::xml_children(node)
      sub_exprs <- kids[xml2::xml_name(kids) == "expr"]
      # Expected: <expr> OP-PLUS <expr>. Unary `+x` is just <expr>; treat as leaf.
      if (length(sub_exprs) != 2L) return(list(node))
      c(collect_plus_terms(sub_exprs[[1L]]),
        collect_plus_terms(sub_exprs[[2L]]))
    }

    # Does a single term look like `<NUM_CONST> * <expr>` or a bare numeric?
    term_has_literal_coef <- function(term_node) {
      kids <- xml2::xml_children(term_node)
      names_kids <- xml2::xml_name(kids)
      # Bare numeric literal (e.g. `1.5` standing as a term).
      if (length(kids) == 1L && names_kids[[1L]] == "NUM_CONST") return(TRUE)
      # `<expr> OP-STAR <expr>` where the first expr is a NUM_CONST leaf.
      star_idx <- which(names_kids == "OP-STAR")
      if (length(star_idx) == 0L) return(FALSE)
      # Use the first OP-STAR (handles `0.3 * a * b` — still counts as literal-coef).
      si <- star_idx[[1L]]
      if (si < 2L) return(FALSE)
      lhs <- kids[[si - 1L]]
      if (xml2::xml_name(lhs) != "expr") return(FALSE)
      lhs_kids <- xml2::xml_children(lhs)
      length(lhs_kids) == 1L &&
        xml2::xml_name(lhs_kids[[1L]]) == "NUM_CONST"
    }

    bad <- lapply(as.list(plus_exprs), function(pe) {
      terms <- collect_plus_terms(pe)
      if (length(terms) < 3L) return(NULL)
      has_lit <- vapply(terms, term_has_literal_coef, logical(1))
      if (!any(has_lit)) return(NULL)

      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(pe, "line1")),
        type        = "warning",
        message     = paste0(
          "R037: composite score with ", length(terms),
          " `+`-joined terms and literal numeric weights -- record weight ",
          "provenance and a sensitivity check, or add ",
          "ANALYSIS_OK[composite-weights]."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

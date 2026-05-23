# R044 -- sentinel-mask assignment from empty-string comparison --------

#' Flag `<name> <- <expr> != ""` / `<name> <- <expr> == ""`.
#'
#' The mask is the partitioner downstream code uses; treating `""` as
#' a missingness sentinel hides the upstream contract and silently
#' drops or keeps rows depending on which side of the comparison the
#' empty string falls on.
#'
#' Scope, on purpose:
#'
#' * Only the empty-string sentinel is matched. `!= 0` / `!is.na(x)`
#'   are out of scope (too common and usually legitimate).
#' * Only top-level assignments to a plain symbol. The inline form
#'   `df[df$col != "", ]` is R005 (`unledger-filter`) territory.
#' * Composition with `&`, `|`, `!`, and parentheses is unwrapped so a
#'   compound mask like `(df$a != "") & (df$b != "")` still fires.
#'
#' Ported from the Python rule `sentinel-mask-assignment`.
#'
#' @keywords internal
sentinel_mask_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # XPath note: the STR_CONST node text for `""` is the two-character
    # string `""` (a quote + a quote). Single-quote delimiters around
    # the XPath literal, then `""` inside.
    comparisons <- xml2::xml_find_all(
      xml,
      "//expr[(NE or EQ) and expr/STR_CONST[text()='\"\"']]"
    )
    if (length(comparisons) == 0L) return(list())

    findings <- list()
    seen_lines <- integer(0)

    for (cmp in as.list(comparisons)) {
      # Walk up through allowed wrapper expressions only (boolean
      # composition / parens). If we cross a subscript (`[`) or a
      # general function call, stop -- that's not a top-level mask
      # assignment.
      cur <- cmp
      assign_node <- NULL
      repeat {
        parent <- xml2::xml_parent(cur)
        if (length(parent) == 0L) break
        if (xml2::xml_name(parent) != "expr") break

        if (length(xml2::xml_find_first(parent, "LEFT_ASSIGN")) > 0L) {
          assign_node <- parent
          break
        }
        if (length(xml2::xml_find_first(parent, "OP-LEFT-BRACKET")) > 0L) {
          break
        }
        if (length(xml2::xml_find_first(parent, "LBB")) > 0L) {
          break
        }
        if (length(xml2::xml_find_first(parent,
                                         "expr/SYMBOL_FUNCTION_CALL")) > 0L) {
          break
        }
        cur <- parent
      }

      if (is.null(assign_node)) next

      # LHS must be a plain symbol (rule out `df$col <- df$x != ""`).
      lhs <- xml2::xml_find_first(assign_node, "expr[1]")
      if (length(lhs) == 0L) next
      lhs_children <- xml2::xml_children(lhs)
      if (length(lhs_children) != 1L ||
          xml2::xml_name(lhs_children[[1]]) != "SYMBOL") {
        next
      }

      line <- as.integer(xml2::xml_attr(assign_node, "line1"))
      if (line %in% seen_lines) next
      seen_lines <- c(seen_lines, line)

      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = source_expression$filename,
        line_number = line,
        type        = "warning",
        message     = paste(
          "R044: boolean mask built from empty-string sentinel --",
          "use is.na() / !is.na() instead, or add",
          "ANALYSIS_OK[sentinel-mask] documenting the upstream contract."
        )
      )
    }
    findings
  })
}

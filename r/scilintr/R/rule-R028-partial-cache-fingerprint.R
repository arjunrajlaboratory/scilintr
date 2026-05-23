# R028 -- Partial cache input fingerprint -----------------------------

#' Flag `digest::digest(<single_SYMBOL>)` inside a function with 2+
#' formals. A cache key that fingerprints a single variable when the
#' enclosing function takes multiple inputs is a partial-fingerprint
#' hazard: un-fingerprinted inputs can change and the cache silently
#' returns stale results.
#'
#' Heuristic: catches `digest::digest(idx_e)` but not
#' `digest::digest(list(N = N, Y = Y, idx_e = idx_e))` because the
#' latter has a function call (`list(...)`) as its argument, not a
#' bare SYMBOL.
#'
#' @keywords internal
partial_cache_fingerprint_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Find `digest::digest(...)` call expressions: the outer `<expr>`
    # whose first child is the `digest::digest` namespace-qualified call.
    digest_calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[",
        "expr[SYMBOL_PACKAGE[text()='digest']",
        " and SYMBOL_FUNCTION_CALL[text()='digest']]",
        " and OP-LEFT-PAREN",
        "]"
      )
    )

    bad <- lapply(as.list(digest_calls), function(call_node) {
      # Positional argument <expr> children come after the leading
      # `digest::digest` <expr>. Identify them.
      arg_exprs <- xml2::xml_find_all(call_node, "expr[position() > 1]")
      if (length(arg_exprs) != 1L) return(NULL)

      # Require the sole argument to be a bare SYMBOL (no nested calls,
      # no list(...)/c(...) wrappers).
      arg <- arg_exprs[[1]]
      children <- xml2::xml_children(arg)
      if (length(children) != 1L) return(NULL)
      if (xml2::xml_name(children[[1]]) != "SYMBOL") return(NULL)

      # Enclosing function literal: nearest ancestor <expr> with a
      # FUNCTION child. Count its SYMBOL_FORMALS.
      fn_ancestor <- xml2::xml_find_first(
        call_node,
        "ancestor::expr[FUNCTION][1]"
      )
      if (inherits(fn_ancestor, "xml_missing")) return(NULL)
      formals <- xml2::xml_find_all(fn_ancestor, "SYMBOL_FORMALS")
      if (length(formals) < 2L) return(NULL)

      line <- as.integer(xml2::xml_attr(call_node, "line1"))
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = line,
        type        = "warning",
        message     = paste0(
          "R028: digest::digest() fingerprints only `",
          xml2::xml_text(children[[1]]),
          "` but the enclosing function takes ", length(formals),
          " inputs -- un-fingerprinted inputs can change and the cache ",
          "will silently return stale results. Fingerprint all inputs ",
          "(e.g. digest::digest(list(...))) or add an ",
          "ANALYSIS_OK[cache-fingerprint] waiver."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

#' R039 -- Recursive calls with constant hyperparameters across depth
#'
#' Flag a recursive function whose self-call passes one of the function's
#' own formal arguments through unchanged. When a hyperparameter that was
#' tuned at the root is inherited verbatim at every recursion depth, the
#' parent-tuned gate becomes a smuggled default at child nodes -- the
#' resulting null at depth then reads as "no further structure" when it
#' really reflects parent-tuned parameters being applied to a different
#' sub-population (see `analysis_lint_strategy.md` section 39).
#'
#' V1 is intentionally conservative and file-local: it finds top-level
#' function definitions `X <- function(...) { ... }`, looks for direct
#' self-calls `X(...)` in the body, and flags when any argument
#' expression is a bare SYMBOL whose name matches one of `X`'s formal
#' arguments. A bare formal pass-through (`recurse(child, gates)`) fires;
#' a transformed value (`recurse(child, child_gates)`) does not.
#'
#' Allowed with `# ANALYSIS_OK[constant-gates-at-depth]` waiver.
#'
#' @keywords internal
constant_gates_recursion_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    fn_defs <- xml2::xml_find_all(
      xml,
      "//expr[(LEFT_ASSIGN or EQ_ASSIGN) and expr[1]/SYMBOL and expr[2]/FUNCTION]"
    )

    out <- list()
    for (def in as.list(fn_defs)) {
      fn_name_node <- xml2::xml_find_first(def, "expr[1]/SYMBOL")
      if (length(fn_name_node) == 0L || is.na(xml2::xml_text(fn_name_node))) next
      fn_name <- xml2::xml_text(fn_name_node)

      formals_nodes <- xml2::xml_find_all(def, ".//SYMBOL_FORMALS")
      formal_names <- vapply(as.list(formals_nodes), xml2::xml_text, character(1))
      if (length(formal_names) == 0L) next

      rec_xpath <- sprintf(
        "expr[2]//SYMBOL_FUNCTION_CALL[text()='%s']/parent::expr/parent::expr",
        fn_name
      )
      rec_calls <- xml2::xml_find_all(def, rec_xpath)

      for (call in as.list(rec_calls)) {
        args <- xml2::xml_find_all(call, "expr")
        if (length(args) < 2L) next
        arg_exprs <- args[-1]

        bad_args <- character(0)
        for (a in as.list(arg_exprs)) {
          children <- xml2::xml_children(a)
          if (length(children) == 1L &&
              xml2::xml_name(children[[1]]) == "SYMBOL") {
            sym <- xml2::xml_text(children[[1]])
            if (sym %in% formal_names) {
              bad_args <- c(bad_args, sym)
            }
          }
        }

        if (length(bad_args) > 0L) {
          out[[length(out) + 1L]] <- lintr::Lint(
            filename    = source_expression$filename,
            line_number = as.integer(xml2::xml_attr(call, "line1")),
            type        = "warning",
            message     = sprintf(
              paste0(
                "R039: recursive call to '%s' passes formal(s) (%s) through unchanged",
                " -- parent-tuned gates become smuggled defaults at depth;",
                " choose per-node gates label-free or add an",
                " ANALYSIS_OK[constant-gates-at-depth] waiver."
              ),
              fn_name,
              paste(unique(bad_args), collapse = ", ")
            )
          )
        }
      }
    }
    out
  })
}

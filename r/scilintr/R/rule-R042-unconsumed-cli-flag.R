# R042 -- optparse flag declared but never read ------------------------

#' Flag `optparse::make_option("--kebab-name", ...)` calls whose
#' parsed dest is never read.
#'
#' Walks every `make_option("--kebab", ...)` (with or without the
#' `optparse::` qualifier), computes the destination name optparse
#' would assign (`--kebab-name` -> `kebab_name`), then checks whether
#' *any* `<args>$<dest>` or `<args>[["<dest>"]]` access reads that
#' name -- where `<args>` is the variable bound to a `parse_args(...)`
#' result. If no parse_args() anchor exists in the file we can't tell
#' what's consumed, so the file is skipped.
#'
#' Ported from the Python rule `unconsumed-cli-flag`.
#'
#' @keywords internal
unconsumed_cli_flag_linter <- function() {
  lintr::Linter(function(source_expression) {
    # make_option(...) declarations and the parse_args() call live in
    # separate top-level expressions, so use the whole-file XML. lintr
    # invokes the linter once per top-level statement and once with the
    # file-level source_expression; only the latter has
    # `full_xml_parsed_content`. Skip the per-statement invocations.
    xml <- source_expression$full_xml_parsed_content
    if (is.null(xml)) return(list())

    # 1. Variables bound to optparse::parse_args(...) (or bare
    #    parse_args(...)) results.
    pa_assigns <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[LEFT_ASSIGN",
        " and expr[1]/SYMBOL",
        " and .//SYMBOL_FUNCTION_CALL[text()='parse_args']]"
      )
    )
    args_names <- character(0)
    for (a in as.list(pa_assigns)) {
      lhs <- xml2::xml_find_first(a, "expr[1]/SYMBOL")
      if (length(lhs) > 0L) args_names <- c(args_names, xml2::xml_text(lhs))
    }
    if (length(args_names) == 0L) return(list())

    # 2. Every make_option("--kebab", ...) call.
    make_option_calls <- xml2::xml_find_all(
      xml,
      "//expr[.//SYMBOL_FUNCTION_CALL[text()='make_option']]"
    )

    declared <- list()
    for (call in as.list(make_option_calls)) {
      first_arg <- xml2::xml_find_first(call, "expr[STR_CONST][1]/STR_CONST")
      if (length(first_arg) == 0L) next
      raw <- xml2::xml_text(first_arg)
      opt_str <- gsub('^["\']|["\']$', "", raw)
      stripped <- sub("^--?", "", opt_str)
      if (!nzchar(stripped)) next
      dest <- gsub("-", "_", stripped)
      declared[[length(declared) + 1L]] <- list(
        call = call,
        dest = dest
      )
    }
    if (length(declared) == 0L) return(list())

    # 3. Every <args_name>$<symbol> and <args_name>[["<str>"]] read.
    read_dests <- character(0)
    for (an in args_names) {
      dollar_reads <- xml2::xml_find_all(
        xml,
        sprintf(
          "//expr[expr/SYMBOL[text()='%s'] and OP-DOLLAR]/SYMBOL",
          an
        )
      )
      read_dests <- c(read_dests,
                      vapply(as.list(dollar_reads), xml2::xml_text,
                             character(1)))

      lbb_reads <- xml2::xml_find_all(
        xml,
        sprintf(
          paste0("//expr[expr/SYMBOL[text()='%s']",
                 " and LBB]/expr/STR_CONST"),
          an
        )
      )
      read_dests <- c(read_dests,
                      gsub('^"|"$', "",
                           vapply(as.list(lbb_reads), xml2::xml_text,
                                  character(1))))
    }

    # 4. Flag every declared dest not in the read set.
    findings <- list()
    for (d in declared) {
      if (d$dest %in% read_dests) next
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(d$call, "line1")),
        type        = "warning",
        message     = paste(
          "R042: CLI flag `", d$dest, "` declared but never read --",
          " either consume it or add ANALYSIS_OK[deprecated-flag]."
        )
      )
    }
    findings
  })
}

# R043 -- yaml/json config read without schema validation --------------

#' Flag `yaml::read_yaml(...)` / `yaml::yaml.load_file(...)` /
#' `jsonlite::fromJSON(...)` results that are later accessed via
#' `$` or `[[ ]]` without an intervening validator call.
#'
#' Track variables whose value comes from one of the loader calls
#' above. If the variable is then read by `<var>$<key>` or
#' `<var>[["<key>"]]`, flag the loader call. If the variable is
#' passed to a `validate_*` or `_schema` function before being
#' read, no finding fires.
#'
#' Ported from the Python rule `unvalidated-config`.
#'
#' @keywords internal
unvalidated_config_linter <- function() {
  LOADERS <- c("read_yaml", "yaml.load_file", "fromJSON")

  lintr::Linter(function(source_expression) {
    # The loader call and the `$` / `[[ ]]` accesses live in different
    # top-level statements, so we need the whole-file XML. lintr
    # invokes the linter once per top-level statement and once with the
    # file-level source_expression; only the latter has
    # `full_xml_parsed_content`. Skip the per-statement invocations.
    xml <- source_expression$full_xml_parsed_content
    if (is.null(xml)) return(list())

    # 1. Variables bound to a loader call. The RHS must be the loader
    #    call itself, not a wrapper around it (`validate_config(yaml::
    #    read_yaml(...))` is the schema-validated path -- don't flag).
    #    `expr[2]/expr[1]//SYMBOL_FUNCTION_CALL` is the function-head
    #    of the outermost call on the RHS.
    loader_predicate <- paste(
      sprintf("expr[2]/expr[1]//SYMBOL_FUNCTION_CALL[text()='%s']", LOADERS),
      collapse = " or "
    )
    loader_assigns <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[LEFT_ASSIGN",
        " and expr[1]/SYMBOL",
        " and (", loader_predicate, ")]"
      )
    )

    # 2. Determine, for each loaded variable, whether it's read via
    #    $/[[ ]] OR passed to a validate-style function.
    findings <- list()
    for (la in as.list(loader_assigns)) {
      lhs <- xml2::xml_find_first(la, "expr[1]/SYMBOL")
      if (length(lhs) == 0L) next
      var_name <- xml2::xml_text(lhs)

      # validator pass-through: <var> is the first arg to a call whose
      # function name matches /(validate|schema)/.
      validator_uses <- xml2::xml_find_all(
        xml,
        sprintf(
          paste0("//expr[expr[1]/SYMBOL_FUNCTION_CALL[",
                 "contains(text(),'validate')",
                 " or contains(text(),'schema')",
                 " or contains(text(),'Schema')]]",
                 "/expr/SYMBOL[text()='%s']"),
          var_name
        )
      )
      if (length(validator_uses) > 0L) next

      # field accesses on the loaded variable.
      dollar_use <- xml2::xml_find_first(
        xml,
        sprintf("//expr[expr/SYMBOL[text()='%s'] and OP-DOLLAR]", var_name)
      )
      lbb_use <- xml2::xml_find_first(
        xml,
        sprintf("//expr[expr/SYMBOL[text()='%s'] and LBB]", var_name)
      )

      if (length(dollar_use) == 0L && length(lbb_use) == 0L) next

      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(la, "line1")),
        type        = "warning",
        message     = paste(
          "R043: config loaded without schema validation --",
          "typos silently drop to NULL, bounds unchecked;",
          "validate before per-key reads or add",
          "ANALYSIS_OK[unvalidated-config]."
        )
      )
    }
    findings
  })
}

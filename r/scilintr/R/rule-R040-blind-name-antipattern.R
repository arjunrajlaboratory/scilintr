#' R040 -- "no-circularity" / "blind" name antipattern
#'
#' A function whose name contains `blind`, `no_circularity`, `unsupervised`,
#' `label_free`, `independent`, or `honest` is asserting that it operates
#' without consulting labels / ground truth. If the body nevertheless
#' references known label columns (e.g. `legacy_branch2_clone`, `truth_c1`,
#' `cell_type`) or label files (e.g. `cell_labels.tsv`), the lexical
#' promise of the name is contradicted by the body -- a classic source of
#' silent circularity in unsupervised analyses.
#'
#' Detection (v1, hardcoded patterns):
#'   * function defs found via `<- function(...)`, `<<- function(...)`, or
#'     `= function(...)` (the `equal_assign` form).
#'   * a function name matching `(blind|no_circularity|unsupervised|
#'     label_free|independent|honest)` is required to trigger inspection.
#'   * body label refs: `$<label>` where the symbol matches a known label
#'     column, or any STR_CONST mentioning `cell_labels` / `labels.<ext>`.
#'
#' Reports at the line of the offending label reference (not the
#' function definition), so a waiver placed near the body works as
#' expected. A `# ANALYSIS_OK[blind-name]:` comment within the waiver
#' window suppresses the finding via the shared waiver layer.
#'
#' @keywords internal
blind_name_antipattern_linter <- function() {
  NAME_RE <- "blind|no_circularity|unsupervised|label_free|independent|honest"
  label_names <- c(
    "legacy_branch2_clone", "cell_type", "treatment", "diagnosis",
    "is_gt", "truth_c1", "gt_label"
  )
  # Bare-symbol tokens whose presence anywhere in the function body is
  # itself a strong signal of a label dependency (e.g. a `labels`
  # parameter being passed through to a merge / join).
  bare_label_symbols <- c("labels", "cell_labels")
  LABEL_PATH_RE <- "cell_labels|labels\\."

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Collect function definitions of the form `<sym> <- function(...) { ... }`
    # and the `equal_assign` variant `<sym> = function(...) { ... }`.
    assign_defs <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[(LEFT_ASSIGN or RIGHT_ASSIGN or EQ_ASSIGN)",
        " and expr[1]/SYMBOL and expr[2]/FUNCTION]"
      )
    )
    eq_defs <- xml2::xml_find_all(
      xml,
      "//equal_assign[expr[1]/SYMBOL and expr[2]/FUNCTION]"
    )
    all_defs <- c(as.list(assign_defs), as.list(eq_defs))
    if (length(all_defs) == 0L) return(list())

    name_pred <- paste0(
      "text()='", label_names, "'", collapse = " or "
    )

    findings <- list()
    for (def in all_defs) {
      name_node <- xml2::xml_find_first(def, "expr[1]/SYMBOL")
      if (length(name_node) == 0L || is.na(xml2::xml_text(name_node))) next
      fn_name <- xml2::xml_text(name_node)
      if (!grepl(NAME_RE, fn_name, perl = TRUE)) next

      # Search inside the function body (expr[2], the FUNCTION expr) for
      # label-column dollar-refs and label-file string literals.
      dollar_hits <- xml2::xml_find_all(
        def,
        paste0(
          "expr[2]//OP-DOLLAR/following-sibling::SYMBOL[",
          name_pred, "]"
        )
      )
      str_hits_all <- xml2::xml_find_all(def, "expr[2]//STR_CONST")
      str_hits <- list()
      for (s in as.list(str_hits_all)) {
        raw <- xml2::xml_text(s)
        val <- gsub('^["\']|["\']$', "", raw)
        if (grepl(LABEL_PATH_RE, val, perl = TRUE)) {
          str_hits[[length(str_hits) + 1L]] <- s
        }
      }

      bare_pred <- paste0(
        "text()='", bare_label_symbols, "'", collapse = " or "
      )
      bare_hits <- xml2::xml_find_all(
        def,
        paste0("expr[2]//SYMBOL[", bare_pred, "]")
      )

      hits <- c(as.list(dollar_hits), str_hits, as.list(bare_hits))
      if (length(hits) == 0L) {
        # Name asserts blind-ness but no label refs in body: nothing to flag.
        next
      }

      # Emit one finding per function, at the line of the first label
      # reference (so a waiver near that reference suppresses it).
      lines <- vapply(
        hits,
        function(h) as.integer(xml2::xml_attr(h, "line1")),
        integer(1)
      )
      first_line <- min(lines)
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = source_expression$filename,
        line_number = first_line,
        type        = "warning",
        message     = paste0(
          "R040: function `", fn_name,
          "` asserts label-independence (name matches `", NAME_RE,
          "`) but body references label data -- either rename to an",
          " evaluation function or add ANALYSIS_OK[blind-name] waiver."
        )
      )
    }

    findings
  })
}

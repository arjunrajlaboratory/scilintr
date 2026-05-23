# R033 -- label-column references in selection-stage files --------------

#' Flag any reference to label / ground-truth columns from inside a file
#' tagged `# STAGE: selection`.
#'
#' Selection-stage code (module scoring, clustering, embedding, calling
#' filters, etc.) must be blind to outcome labels. The project enforces a
#' two-file split: `selected_calls.csv` (labels-free) is written by the
#' selection-stage script, and `selected_calls_evaluated.csv` is produced
#' downstream by an evaluation-stage script that joins labels. Even a
#' read-only label reference in a selection-stage file makes the leak
#' "one careless edit away."
#'
#' Stage detection: scan the first 10 lines of the file for a comment
#' `# STAGE: <name>`. The linter fires *only* when `<name>` is
#' exactly `selection`. Other stages (including untagged files) are
#' handled by other rules (e.g. R012 covers all blind stages).
#'
#' Detection patterns (label names hardcoded for v1):
#'   * `df$<label>`        -- `OP-DOLLAR` followed by `SYMBOL` matching a label
#'   * `df[["<label>"]]`   -- string literal inside `[[ ]]` matching a label
#'   * `pull(<label>)`     -- bare `SYMBOL` argument to `pull()` / `select()`
#'
#' @keywords internal
label_ref_in_selection_linter <- function() {
  label_names <- c(
    "legacy_branch2_clone", "legacy_clone", "cell_type",
    "treatment", "diagnosis", "condition",
    "is_gt", "truth", "gt_label"
  )
  label_set <- as.character(label_names)

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    filename <- source_expression$filename
    if (is.null(filename) || !nzchar(filename) || !file.exists(filename)) {
      return(list())
    }

    stage <- detect_file_stage(filename)
    if (is.na(stage) || !identical(stage, "selection")) return(list())

    findings <- list()
    name_pred <- paste0("text()='", label_set, "'", collapse = " or ")

    # Pattern A: df$label -- OP-DOLLAR followed by matching SYMBOL.
    dollar_syms <- xml2::xml_find_all(
      xml,
      paste0("//OP-DOLLAR/following-sibling::SYMBOL[", name_pred, "]")
    )
    for (node in as.list(dollar_syms)) {
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R033: label-column reference `$", xml2::xml_text(node),
          "` in a selection-stage file -- split label use into a separate",
          " `# STAGE: evaluation` script (see analysis_lint_strategy.md #33)."
        )
      )
    }

    # Pattern B: df[["label"]] -- STR_CONST inside an LBB bracket expr.
    str_nodes <- xml2::xml_find_all(
      xml,
      "//LBB/following-sibling::expr/STR_CONST"
    )
    for (node in as.list(str_nodes)) {
      raw <- xml2::xml_text(node)
      val <- gsub('^["\']|["\']$', "", raw)
      if (val %in% label_set) {
        findings[[length(findings) + 1L]] <- lintr::Lint(
          filename    = filename,
          line_number = as.integer(xml2::xml_attr(node, "line1")),
          type        = "warning",
          message     = paste0(
            "R033: label-column reference `[[\"", val,
            "\"]]` in a selection-stage file -- split label use into a",
            " separate `# STAGE: evaluation` script."
          )
        )
      }
    }

    # Pattern C: pull(<label>) or select(<label>) -- bare SYMBOL arg.
    call_syms <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[",
        "text()='pull' or text()='select'",
        "]]/expr/SYMBOL[", name_pred, "]"
      )
    )
    for (node in as.list(call_syms)) {
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R033: label-column reference `", xml2::xml_text(node),
          "` passed to dplyr verb in a selection-stage file -- split",
          " label use into a separate `# STAGE: evaluation` script."
        )
      )
    }

    findings
  })
}

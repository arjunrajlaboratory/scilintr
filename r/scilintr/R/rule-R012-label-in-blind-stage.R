# R012 -- label-column references in blind (selection) stages ----------

#' Flag references to label / ground-truth column names in files that
#' are tagged `# STAGE: selection` (or any non-evaluation blind stage).
#'
#' Selection-stage code (PCA, HVG, clustering, embedding, etc.) must be
#' blind to outcome/label columns; touching `metadata$treatment` while
#' choosing genes leaks the answer key into the unsupervised pipeline.
#'
#' Stage detection: scan the first 10 lines of the file for a comment
#' `# STAGE: <name>`. If `<name>` is `evaluation` (or no tag is present)
#' the linter does not fire. Anything else (including `selection`) is
#' treated as a blind stage.
#'
#' Detection patterns (label names hardcoded for v1):
#'   * `metadata$<label>`     -- `OP-DOLLAR` followed by `SYMBOL` matching a label
#'   * `df[["<label>"]]`      -- string literal inside `[[ ]]` matching a label
#'   * `pull(<label>)`        -- bare `SYMBOL` argument to `pull()`
#'
#' @keywords internal
label_in_blind_stage_linter <- function() {
  label_names <- c(
    "treatment", "condition", "phenotype", "diagnosis", "response",
    "outcome", "case", "control", "treated", "responder", "contrast",
    "label", "class", "group", "cell_type", "legacy_branch2_clone",
    "legacy_clone", "is_gt", "gt_label", "truth"
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
    # Only fire in blind (non-evaluation) tagged stages.
    if (is.na(stage) || identical(stage, "evaluation")) return(list())

    findings <- list()

    name_pred <- paste0("text()='", label_set, "'", collapse = " or ")

    # Pattern A: metadata$treatment -- OP-DOLLAR followed by matching SYMBOL.
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
          "R012: reference to label column `$", xml2::xml_text(node),
          "` in a blind (`STAGE: ", stage, "`) file -- selection-stage code",
          " must not consult outcome/label metadata."
        )
      )
    }

    # Pattern B: df[["treatment"]] -- STR_CONST inside an LBB bracket expr.
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
            "R012: reference to label column `[[\"", val,
            "\"]]` in a blind (`STAGE: ", stage, "`) file -- selection-stage",
            " code must not consult outcome/label metadata."
          )
        )
      }
    }

    # Pattern C: pull(<label>) -- SYMBOL argument inside a pull() call.
    pull_syms <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='pull']]",
        "/expr/SYMBOL[", name_pred, "]"
      )
    )
    for (node in as.list(pull_syms)) {
      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste0(
          "R012: reference to label column `pull(", xml2::xml_text(node),
          ")` in a blind (`STAGE: ", stage, "`) file -- selection-stage code",
          " must not consult outcome/label metadata."
        )
      )
    }

    findings
  })
}

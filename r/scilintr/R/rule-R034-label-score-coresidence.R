# R034 -- label / score co-residence in selection-stage output CSV -------

#' Flag a `data.frame(...)` literal that mixes label columns with
#' computed-score columns and is subsequently written to disk via
#' `write.csv` / `write_csv` from within a `# STAGE: selection` file.
#'
#' Rationale: a CSV that pairs labels with discovery scores propagates
#' the leakage risk downstream -- any later script that re-reads the
#' file is "one careless edit away" from training on labels. The
#' project-prescribed remediation is the two-file split (selection
#' writes `selected_calls.csv`, labels-free; evaluation joins labels in
#' a separate stage). See `analysis_lint_strategy.md` #34.
#'
#' v1 detection (single file):
#'   1. Stage gate -- only fire when the first 10 lines contain
#'      `# STAGE: selection`.
#'   2. Find `data.frame(...)` calls whose argument list contains both
#'      a SYMBOL_SUB matching a label name and a SYMBOL_SUB matching a
#'      score-name regex.
#'   3. Require the file to also contain a `write.csv` /
#'      `write_csv` / `readr::write_csv` call (proxy for "written to
#'      disk"). Flag at the line of the `data.frame` call.
#'
#' @keywords internal
label_score_coresidence_linter <- function() {
  label_names <- c(
    "legacy_branch2_clone", "legacy_clone", "cell_type",
    "treatment", "diagnosis", "is_gt", "truth", "gt_label"
  )
  score_regex <- "^(score|confidence|lr|posterior|precision|recall|ari|nmi|accuracy)$"

  lintr::Linter(function(source_expression) {
    # R034 spans expressions (data.frame in one top-level statement,
    # write.csv in another), so we use the full-file XML. lintr calls
    # the linter once per top-level expression and once with the
    # file-level source_expression; only the latter has
    # `full_xml_parsed_content`. Skip the per-expression invocations.
    xml <- source_expression$full_xml_parsed_content
    if (is.null(xml)) return(list())

    filename <- source_expression$filename
    if (is.null(filename) || !nzchar(filename) || !file.exists(filename)) {
      return(list())
    }

    stage <- detect_file_stage(filename)
    if (is.na(stage) || !identical(stage, "selection")) return(list())

    # Require the file to write a CSV (proxy for "written to disk").
    write_calls <- xml2::xml_find_all(
      xml,
      paste0(
        "//SYMBOL_FUNCTION_CALL[",
        "text()='write.csv' or text()='write_csv'",
        "]"
      )
    )
    if (length(write_calls) == 0L) return(list())

    # Find every data.frame(...) call expression.
    df_calls <- xml2::xml_find_all(
      xml,
      "//expr[expr/SYMBOL_FUNCTION_CALL[text()='data.frame']]"
    )
    if (length(df_calls) == 0L) return(list())

    label_pred <- paste0(
      "text()='", as.character(label_names), "'",
      collapse = " or "
    )

    findings <- list()
    for (call in as.list(df_calls)) {
      # All named-argument identifiers inside this data.frame(...) call.
      sub_nodes <- xml2::xml_find_all(call, ".//SYMBOL_SUB")
      if (length(sub_nodes) == 0L) next
      sub_text <- xml2::xml_text(sub_nodes)

      has_label <- any(sub_text %in% label_names)
      has_score <- any(grepl(score_regex, sub_text, perl = TRUE))
      if (!(has_label && has_score)) next

      # Anchor the lint at the first matching SYMBOL_SUB (label or
      # score) in document order -- gives the reader the earliest
      # offending column. sub_nodes is already in source order.
      matches <- which(
        sub_text %in% label_names |
        grepl(score_regex, sub_text, perl = TRUE)
      )
      anchor_node <- sub_nodes[[matches[1L]]]
      line_no <- as.integer(xml2::xml_attr(anchor_node, "line1"))

      label_hits <- sub_text[sub_text %in% label_names]
      hit_label <- label_hits[1L]
      score_hits <- sub_text[grepl(score_regex, sub_text, perl = TRUE)]
      score_msg <- paste(unique(score_hits), collapse = ", ")

      findings[[length(findings) + 1L]] <- lintr::Lint(
        filename    = filename,
        line_number = line_no,
        type        = "warning",
        message     = paste0(
          "R034: `data.frame(...)` in a selection-stage file mixes label ",
          "column `", hit_label, "` with score column(s) `", score_msg,
          "` and is written to CSV -- split into two files (selection ",
          "writes labels-free; evaluation joins labels). See ",
          "analysis_lint_strategy.md #34."
        )
      )
    }

    findings
  })
}

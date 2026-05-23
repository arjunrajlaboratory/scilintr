#' Registry of per-file `lintr::Linter()` factories.
#'
#' Each entry is `R<NN> = factory()`. The registry key becomes the
#' rule ID on every emitted Lint (via `lintr`'s name propagation).
#'
#' Add new per-file rules here as they are implemented. Cross-file
#' rules live in `R/cross_file_rules.R`.
#'
#' @keywords internal
per_file_linters <- function() {
  list(
    R001 = positional_access_linter(),
    R002 = magic_threshold_linter(),
    R003 = unchecked_join_linter(),
    R004 = positional_alignment_linter(),
    R005 = unledger_filter_linter(),
    R006 = unledger_missingness_linter(),
    R007 = broad_exception_linter(),
    R008 = implicit_file_selection_linter(),
    R009 = stale_cache_linter(),
    R010 = synthetic_data_linter(),
    R011 = unseeded_stochastic_linter(),
    R012 = label_in_blind_stage_linter(),
    R013 = hardcoded_design_formula_linter(),
    R014 = unexplained_transform_linter(),
    R015 = ambiguous_layer_linter(),
    R016 = hardcoded_sample_id_linter(),
    R017 = warning_suppression_linter(),
    R018 = unchecked_convergence_linter(),
    R019 = plot_data_filter_linter(),
    R021 = patient_id_in_lib_linter(),
    R022 = seed_in_loop_linter(),
    R023 = plot_clip_linter(),
    R024 = smuggled_default_linter(),
    R027 = env_validator_asymmetry_linter(),
    R028 = partial_cache_fingerprint_linter(),
    R029 = readcsv_mangling_linter(),
    R030 = silent_trycatch_linter(),
    R031 = magic_eps_floor_linter(),
    R032 = label_tiebreak_linter(),
    R033 = label_ref_in_selection_linter(),
    R034 = label_score_coresidence_linter(),
    R035 = label_tainted_input_linter(),
    R036 = threshold_near_label_linter(),
    R037 = composite_weights_linter(),
    R038 = symmetric_best_linter(),
    R039 = constant_gates_recursion_linter(),
    R040 = blind_name_antipattern_linter(),
    R041 = return_null_on_missing_linter(),
    R042 = unconsumed_cli_flag_linter(),
    R043 = unvalidated_config_linter(),
    R044 = sentinel_mask_linter()
  )
}


# R030 -- silent tryCatch error swallowing ------------------------------

#' Flag `tryCatch(..., error = function(e) <literal>)`.
#'
#' A handler that returns a single literal (NUM_CONST, NULL_CONST,
#' STR_CONST -- covers `NA`, `NA_real_`, `NULL`, `0`, `""`, etc.)
#' silently maps errors to a numerically-valid stand-in. Caller-side
#' arithmetic then continues with a meaningless value.
#'
#' Multi-statement handler bodies (`function(e) { warning(...); NA }`)
#' are not flagged here -- they may still swallow, but they at least
#' do *something* observable. A stricter variant could check the last
#' statement of a `{...}` body; deferred for now.
#'
#' @keywords internal
silent_trycatch_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Find every `function(...) <body>` that's the value of an `error =`
    # named argument inside a `tryCatch(...)` call.
    handlers <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='tryCatch']]",
        "//SYMBOL_SUB[text()='error']",
        "/following-sibling::expr[1][FUNCTION]"
      )
    )

    bad <- lapply(as.list(handlers), function(h) {
      body <- xml2::xml_find_first(h, "expr[last()]")
      if (length(body) == 0L) return(NULL)
      children <- xml2::xml_children(body)
      if (length(children) != 1L) return(NULL)
      tag <- xml2::xml_name(children[[1]])
      if (!tag %in% c("NUM_CONST", "NULL_CONST", "STR_CONST")) {
        return(NULL)
      }
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(body, "line1")),
        type        = "warning",
        message     = paste(
          "R030: tryCatch swallows error and returns a literal --",
          "log explicitly or rethrow."
        )
      )
    })

    bad[!vapply(bad, is.null, logical(1))]
  })
}

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

#' Flag a `tryCatch(..., error = ...)` handler that silently degrades.
#'
#' The silent-fallback family in three costumes, all sharing one hidden
#' commitment -- "on failure this quietly proceeds on a meaningless
#' value instead of stopping":
#'
#' \itemize{
#'   \item \strong{return}: the handler's return value is a bare literal
#'     (NUM_CONST, NULL_CONST, STR_CONST -- `NA`, `NA_real_`, `NULL`,
#'     `0`, `""`, ...), whether returned directly
#'     (`function(e) NA`) or as the last statement of a multi-statement
#'     block (`function(e) { warning(...); NA }`). Caller-side code then
#'     continues with a numerically-valid stand-in.
#'   \item \strong{rebind}: the handler superassigns (`<<-`) an outer
#'     name to a degraded default (`cohort <<- NULL`), so downstream
#'     stages run on a placeholder. `<<-` escapes the handler scope, so
#'     it is flagged wherever it sits in the body.
#'   \item \strong{stub}: the handler superassigns an outer name to a
#'     no-op stub function (`score_fn <<- function(...) NULL`), silently
#'     disabling behavior on the failure path.
#' }
#'
#' Doing real work and returning a genuine recovered value (a cached
#' object, an alternate computation, `stop(e)` to rethrow) is left
#' alone -- only bare placeholders and no-op stubs are flagged. Local
#' (`<-`) rebinds are not flagged: in R they die with the handler frame
#' and have no external effect.
#'
#' @keywords internal
silent_trycatch_linter <- function() {
  literal_tags <- c("NUM_CONST", "NULL_CONST", "STR_CONST")

  # An <expr> that is a single bare constant (`NA` / `NULL` / `0` / "").
  is_bare_literal <- function(node) {
    if (length(node) == 0L) return(FALSE)
    kids <- xml2::xml_children(node)
    length(kids) == 1L && xml2::xml_name(kids[[1]]) %in% literal_tags
  }

  # Direct-child <expr> statements of a handler body: the statements of
  # a `{...}` block, or the single expression if the body is not a block.
  body_statements <- function(body) {
    kids <- xml2::xml_children(body)
    if (length(kids) > 0L && xml2::xml_name(kids[[1]]) == "OP-LEFT-BRACE") {
      as.list(xml2::xml_find_all(body, "expr"))
    } else {
      list(body)
    }
  }

  # A `function(...) <noop>` whose body evaluates to a bare literal.
  is_stub_function <- function(node) {
    if (length(node) == 0L) return(FALSE)
    if (length(xml2::xml_find_first(node, "FUNCTION")) == 0L) return(FALSE)
    fbody <- xml2::xml_find_first(node, "expr[last()]")
    if (length(fbody) == 0L) return(FALSE)
    stmts <- body_statements(fbody)
    length(stmts) > 0L && is_bare_literal(stmts[[length(stmts)]])
  }

  lintr::Linter(function(source_expression) {
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Every `function(...) <body>` that's the value of an `error =`
    # named argument inside a `tryCatch(...)` call.
    handlers <- xml2::xml_find_all(
      xml,
      paste0(
        "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='tryCatch']]",
        "//SYMBOL_SUB[text()='error']",
        "/following-sibling::expr[1][FUNCTION]"
      )
    )

    lints <- list()
    emit <- function(node, why) {
      lints[[length(lints) + 1L]] <<- lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = paste("R030:", why)
      )
    }

    for (h in as.list(handlers)) {
      body <- xml2::xml_find_first(h, "expr[last()]")
      if (length(body) == 0L) next
      stmts <- body_statements(body)
      if (length(stmts) == 0L) next

      # return costume -- the handler's return value is a bare literal.
      last <- stmts[[length(stmts)]]
      if (is_bare_literal(last)) {
        emit(last, paste(
          "tryCatch error handler returns a bare literal --",
          "the failure path silently substitutes a placeholder;",
          "log explicitly or rethrow."
        ))
      }

      # rebind / stub costume -- a `<<-` on the failure path rebinds an
      # outer name to a degraded default or a no-op stub. `<<-` escapes
      # the handler scope and still runs when guarded by control flow
      # (`if (...) cohort <<- NULL`), so search the whole body, not just
      # the top-level statements. `<-` and `<<-` share the LEFT_ASSIGN
      # token, so disambiguate on the operator text.
      assigns <- xml2::xml_find_all(body, ".//expr[LEFT_ASSIGN]")
      for (s in as.list(assigns)) {
        if (xml2::xml_text(xml2::xml_find_first(s, "LEFT_ASSIGN")) != "<<-") next
        rhs <- xml2::xml_find_first(s, "expr[last()]")
        if (is_bare_literal(rhs)) {
          emit(s, paste(
            "tryCatch error handler superassigns a degraded default",
            "(NA/NULL/0/...) -- the analysis silently continues on a",
            "placeholder; recover a real value or rethrow."
          ))
        } else if (is_stub_function(rhs)) {
          emit(s, paste(
            "tryCatch error handler superassigns a no-op stub function",
            "-- the failure path silently disables behavior; provide a",
            "real fallback or rethrow."
          ))
        }
      }
    }

    lints
  })
}

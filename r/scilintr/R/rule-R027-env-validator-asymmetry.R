#' R027 -- Asymmetric env_* validators within a single file
#'
#' Flag when a single source file defines two or more `env_*`-named
#' helper functions that mix two failure styles: some return a default
#' (silent fall-through) while others halt loudly via `stop()`.
#' Inconsistency here breeds silent misconfiguration: callers cannot
#' predict whether a missing env var crashes or quietly drifts.
#'
#' Pragmatic v1: regex over the file text plus a top-level XML check.
#' Emit a single lint at the line of the FIRST `env_*` function definition
#' in the file (the source_expression covering that def is the only one
#' that emits, to keep results stable across lintr's per-expression model).
#'
#' @keywords internal
env_validator_asymmetry_linter <- function() {
  lintr::Linter(function(source_expression) {
    if (is.null(source_expression$filename)) return(list())
    xml <- source_expression$xml_parsed_content
    if (is.null(xml)) return(list())

    # Find env_* function definitions in THIS source expression.
    env_defs <- xml2::xml_find_all(
      xml,
      "//expr[(LEFT_ASSIGN or EQ_ASSIGN) and expr[2]/FUNCTION and starts-with(expr[1]/SYMBOL/text(), 'env_')]"
    )
    if (length(env_defs) == 0L) return(list())

    # Read the whole file for file-level analysis.
    file_text <- tryCatch(
      paste(readLines(source_expression$filename, warn = FALSE), collapse = "\n"),
      error = function(e) NA_character_
    )
    if (is.na(file_text)) return(list())

    env_def_positions <- gregexpr("env_\\w+\\s*<-\\s*function", file_text, perl = TRUE)[[1]]
    if (env_def_positions[1] == -1L || length(env_def_positions) < 2L) return(list())

    has_halt    <- grepl("stop\\(", file_text)
    has_default <- grepl("return\\(default\\)|<-\\s*default\\b", file_text, perl = TRUE)
    if (!(has_halt && has_default)) return(list())

    # Only the source_expression containing the FIRST env_* def emits.
    first_pos <- env_def_positions[1]
    prefix <- substr(file_text, 1L, first_pos - 1L)
    newlines_before <- gregexpr("\n", prefix, fixed = TRUE)[[1]]
    first_line <- if (newlines_before[1] == -1L) 1L else (length(newlines_before) + 1L)

    this_def_line <- as.integer(xml2::xml_attr(env_defs[[1]], "line1"))
    if (!isTRUE(this_def_line == first_line)) return(list())

    list(lintr::Lint(
      filename    = source_expression$filename,
      line_number = first_line,
      type        = "warning",
      message     = paste0(
        "R027: env_* validators mix halting (stop()) and default-fallback ",
        "styles in the same module -- pick one policy so callers can predict ",
        "whether a missing env var crashes or silently drifts."
      )
    ))
  })
}

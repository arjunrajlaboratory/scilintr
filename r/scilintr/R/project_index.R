#' Build a project-wide index for cross-file analysis.
#'
#' Walks every `.R` file once and collects:
#'
#' - top-level function definitions (name, file, line)
#' - `source()` edges (file, sourced_file)
#' - stage tags per file (from `# STAGE: <name>` headers)
#'
#' All file paths are normalized to absolute paths so cross-file
#' joins match cleanly regardless of how the caller passed them in.
#'
#' @keywords internal
build_project_index <- function(files, config = NULL) {
  if (length(files) == 0L) {
    return(list(
      files   = character(),
      defs    = empty_defs(),
      sources = empty_sources(),
      reads   = empty_reads(),
      writes  = empty_writes(),
      stage   = empty_stages()
    ))
  }
  files_abs <- vapply(files, function(f) normalizePath(f, mustWork = FALSE),
                      character(1))

  defs_list <- vector("list", length(files))
  sources_list <- vector("list", length(files))
  stages_list <- vector("list", length(files))

  for (i in seq_along(files)) {
    info <- parse_file_info(files[i], files_abs[i])
    if (is.null(info)) next
    defs_list[[i]]    <- info$defs
    sources_list[[i]] <- info$sources
    stages_list[[i]]  <- info$stage
  }

  combine <- function(lst, empty) {
    lst <- lst[!vapply(lst, is.null, logical(1))]
    if (length(lst) == 0L) return(empty)
    do.call(rbind, lst)
  }

  list(
    files   = files_abs,
    defs    = combine(defs_list,    empty_defs()),
    sources = combine(sources_list, empty_sources()),
    reads   = empty_reads(),
    writes  = empty_writes(),
    stage   = combine(stages_list,  empty_stages())
  )
}

#' Parse a single file and pull defs, sources, and stage tag.
#' @keywords internal
parse_file_info <- function(path, path_abs) {
  parsed <- tryCatch(
    parse(file = path, keep.source = TRUE),
    error = function(e) NULL
  )
  if (is.null(parsed) || length(parsed) == 0L) return(NULL)

  xml_text <- tryCatch(
    xmlparsedata::xml_parse_data(parsed),
    error = function(e) NULL
  )
  if (is.null(xml_text) || !nzchar(xml_text)) return(NULL)

  xml <- tryCatch(xml2::read_xml(xml_text), error = function(e) NULL)
  if (is.null(xml)) return(NULL)

  list(
    defs    = extract_fn_defs(xml, path_abs),
    sources = extract_sources(xml, path, path_abs),
    stage   = stage_row(path, path_abs)
  )
}

#' Top-level function definitions in a parsed file.
#'
#' Handles both `name <- function(...)` and `name = function(...)`.
#' Skips `->` (right-assign) and `<<-` (super-assign) for v0; those
#' are rare in research code and produce a different XML shape.
#'
#' @keywords internal
extract_fn_defs <- function(xml, file_abs) {
  left_defs <- xml2::xml_find_all(
    xml,
    "//expr[LEFT_ASSIGN and expr[1]/SYMBOL and expr[2]/FUNCTION]"
  )
  eq_defs <- xml2::xml_find_all(
    xml,
    "//equal_assign[expr[1]/SYMBOL and expr[2]/FUNCTION]"
  )
  all_defs <- c(as.list(left_defs), as.list(eq_defs))
  if (length(all_defs) == 0L) return(empty_defs())

  rows <- lapply(all_defs, function(node) {
    sym <- xml2::xml_find_first(node, "expr[1]/SYMBOL")
    if (length(sym) == 0L) return(NULL)
    data.frame(
      name = xml2::xml_text(sym),
      file = file_abs,
      line = as.integer(xml2::xml_attr(node, "line1")),
      stringsAsFactors = FALSE
    )
  })
  rows <- rows[!vapply(rows, is.null, logical(1))]
  if (length(rows) == 0L) return(empty_defs())
  do.call(rbind, rows)
}

#' `source()` / `sys.source()` edges out of a file.
#'
#' Only handles the literal-string form (`source("file.R")`); dynamic
#' source(get(...)) etc. is ignored. Paths are resolved relative to
#' the consumer file's directory and normalized to absolute.
#'
#' @keywords internal
extract_sources <- function(xml, file_path, file_abs) {
  src_calls <- xml2::xml_find_all(
    xml,
    paste(
      "//expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='source']]",
      "| //expr[expr[1]/SYMBOL_FUNCTION_CALL[text()='sys.source']]"
    )
  )
  if (length(src_calls) == 0L) return(empty_sources())

  rows <- lapply(as.list(src_calls), function(node) {
    str_const <- xml2::xml_find_first(node, "./expr/STR_CONST")
    if (length(str_const) == 0L) return(NULL)
    raw <- xml2::xml_text(str_const)
    sourced <- gsub("^[\"']|[\"']$", "", raw)

    sourced_abs <- normalizePath(
      file.path(dirname(file_path), sourced),
      mustWork = FALSE
    )
    data.frame(
      file = file_abs,
      sourced_file = sourced_abs,
      stringsAsFactors = FALSE
    )
  })
  rows <- rows[!vapply(rows, is.null, logical(1))]
  if (length(rows) == 0L) return(empty_sources())
  do.call(rbind, rows)
}

#' Stage tag row for the index -- wraps `detect_file_stage()`.
#' @keywords internal
stage_row <- function(path, path_abs) {
  data.frame(
    file = path_abs,
    stage = detect_file_stage(path),
    stringsAsFactors = FALSE
  )
}

# Empty-table helpers ----------------------------------------------------

empty_defs <- function() data.frame(
  name = character(), file = character(),
  line = integer(), stringsAsFactors = FALSE
)
empty_sources <- function() data.frame(
  file = character(), sourced_file = character(),
  stringsAsFactors = FALSE
)
empty_reads <- function() data.frame(
  file = character(), line = integer(), path = character(),
  stringsAsFactors = FALSE
)
empty_writes <- function() data.frame(
  file = character(), line = integer(), path = character(),
  stringsAsFactors = FALSE
)
empty_stages <- function() data.frame(
  file = character(), stage = character(),
  stringsAsFactors = FALSE
)

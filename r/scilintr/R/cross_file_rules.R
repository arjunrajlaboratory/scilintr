#' Registry of cross-file (project-level) rules.
#'
#' Each entry is `R<NN> = function(idx) <findings>`. The rule receives
#' the project index built by `build_project_index()` and returns a
#' list of `scilintr_finding` records.
#'
#' Add new cross-file rules here as they are implemented.
#'
#' @keywords internal
cross_file_rules <- function() {
  list(
    R020 = rule_R020_shadow_overwrite,
    R025 = rule_R025_def_drift,
    R026 = rule_R026_dead_code
  )
}


# R020 -- shadow-overwrite ----------------------------------------------

#' Flag a top-level function definition that shadows a name imported
#' via `source()`.
#'
#' Joins the project's `defs` table (one row per top-level function
#' definition) with its `sources` table (one row per `source()` edge)
#' and looks for names defined in both the consumer file and the
#' sourced file. The finding lands on the consumer's redefinition line.
#'
#' @keywords internal
rule_R020_shadow_overwrite <- function(idx) {
  if (nrow(idx$defs) == 0L)    return(list())
  if (nrow(idx$sources) == 0L) return(list())

  edges <- idx$sources
  defs  <- idx$defs

  findings <- list()
  for (i in seq_len(nrow(edges))) {
    consumer <- edges$file[i]
    sourced  <- edges$sourced_file[i]

    cons_defs <- defs[defs$file == consumer, , drop = FALSE]
    lib_defs  <- defs[defs$file == sourced,  , drop = FALSE]
    if (nrow(cons_defs) == 0L || nrow(lib_defs) == 0L) next

    overlap <- merge(cons_defs, lib_defs, by = "name",
                     suffixes = c(".consumer", ".lib"))
    if (nrow(overlap) == 0L) next

    for (j in seq_len(nrow(overlap))) {
      findings[[length(findings) + 1L]] <- Finding(
        file = overlap$file.consumer[j],
        line = overlap$line.consumer[j],
        rule = "R020",
        message = sprintf(
          paste(
            "R020: function '%s' redefined after source('%s') --",
            "shadows the library version (defined at %s:%d)."
          ),
          overlap$name[j],
          basename(sourced),
          basename(overlap$file.lib[j]),
          overlap$line.lib[j]
        )
      )
    }
  }
  findings
}


# R025 -- cross-file definition drift -----------------------------------

#' Flag function names defined in more than one file.
#'
#' Groups `idx$defs` by function `name`; if a name has definitions in
#' more than one file, emits a Finding at each definition site so the
#' user sees every drift location. Waivers (`ANALYSIS_OK[...]`) at any
#' individual site are applied by the cross-file waiver filter and can
#' suppress that site independently (e.g. for intentional v1/v2 kept
#' alongside each other).
#'
#' @keywords internal
rule_R025_def_drift <- function(idx) {
  if (nrow(idx$defs) == 0L) return(list())

  counts <- table(idx$defs$name)
  drifted_names <- names(counts)[counts > 1]
  if (length(drifted_names) == 0L) return(list())

  out <- list()
  for (nm in drifted_names) {
    rows <- idx$defs[idx$defs$name == nm, , drop = FALSE]
    # Only flag if the definitions span multiple files (drift, not
    # accidental duplicates within one file -- those are a per-file
    # concern).
    if (length(unique(rows$file)) < 2L) next
    for (i in seq_len(nrow(rows))) {
      out[[length(out) + 1L]] <- Finding(
        file = rows$file[i],
        line = rows$line[i],
        rule = "R025",
        message = sprintf(
          "R025: function '%s' defined in %d files; drift hazard.",
          nm, length(unique(rows$file))
        )
      )
    }
  }
  out
}


# R026 -- dead / unused code --------------------------------------------

#' Flag top-level function definitions that have no callers in any
#' other project file.
#'
#' For each function in `idx$defs`, scans the text of every other `.R`
#' file in `idx$files` for a token matching `\bfn_name\s*\(`. If no
#' such call site is found, the definition is reported as dead code at
#' its def line. Callers within the defining file are tolerated (they
#' usually indicate internal helpers); intentional API stubs should
#' carry an `ANALYSIS_OK[unused-fn]` waiver near the def. This is a
#' v1 textual check, so matches inside comments or strings are not
#' excluded.
#'
#' @importFrom stats setNames
#' @keywords internal
rule_R026_dead_code <- function(idx) {
  if (nrow(idx$defs) == 0L) return(list())

  file_texts <- setNames(
    vapply(idx$files, function(f) {
      paste(readLines(f, warn = FALSE), collapse = "\n")
    }, character(1)),
    idx$files
  )

  escape_regex <- function(s) {
    gsub("([.\\+*?^$()\\[\\]{}|])", "\\\\\\1", s, perl = TRUE)
  }

  out <- list()
  for (i in seq_len(nrow(idx$defs))) {
    nm       <- idx$defs$name[i]
    def_file <- idx$defs$file[i]

    other_files <- setdiff(idx$files, def_file)
    pattern <- sprintf("\\b%s\\s*\\(", escape_regex(nm))

    has_caller <- FALSE
    for (f in other_files) {
      if (grepl(pattern, file_texts[[f]], perl = TRUE)) {
        has_caller <- TRUE
        break
      }
    }
    if (!has_caller) {
      out[[length(out) + 1L]] <- Finding(
        file = def_file,
        line = idx$defs$line[i],
        rule = "R026",
        message = sprintf(
          "R026: function '%s' has no callers in other project files -- dead code.",
          nm
        )
      )
    }
  }
  out
}

# EXPECTED: R007 at line 5

counts <- NULL
# silent try — no log, no rethrow
counts <- try(load_counts("/path/that/might/fail"), silent = TRUE)

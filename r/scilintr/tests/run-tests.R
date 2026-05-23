# Run the testthat suite using in-source loading (no install required).
setwd(file.path("..", "scilintr"))
library(testthat)

# Stub the namespace by sourcing R/ into a fresh env.
env <- new.env(parent = globalenv())
for (f in list.files("R", pattern = "\\.R$", full.names = TRUE)) {
  source(f, local = env)
}

# Expose lint_file / lint_project / helpers as globals so test files find them.
for (nm in ls(env)) assign(nm, get(nm, envir = env), envir = globalenv())

results <- test_dir("tests/testthat", reporter = "summary",
                   stop_on_failure = FALSE)
df <- as.data.frame(results)
cat("\n=== Summary ===\n")
cat("passed: ", sum(df$passed), "\n", sep = "")
cat("failed: ", sum(df$failed), "\n", sep = "")
cat("skipped:", sum(df$skipped), "\n", sep = "")
cat("warning:", sum(df$warning), "\n", sep = "")
cat("total tests:", nrow(df), "\n")

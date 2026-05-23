# EXPECTED: R042 at line 5

opt_list <- list(
  optparse::make_option("--top-modules", default = 25L),
  optparse::make_option("--band-lo",     default = 0.22)
)
opt <- optparse::parse_args(optparse::OptionParser(option_list = opt_list))

# band_lo is declared but never read; only top_modules is used.
cat("top modules:", opt$top_modules, "\n")

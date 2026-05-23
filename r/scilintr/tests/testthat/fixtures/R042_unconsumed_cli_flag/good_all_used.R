opt_list <- list(
  optparse::make_option("--top-modules", default = 25L),
  optparse::make_option("--band-lo",     default = 0.22),
  optparse::make_option("--seed",        default = 42L)
)
opt <- optparse::parse_args(optparse::OptionParser(option_list = opt_list))

set.seed(opt$seed)
cat("top:", opt$top_modules, "lo:", opt$band_lo, "\n")

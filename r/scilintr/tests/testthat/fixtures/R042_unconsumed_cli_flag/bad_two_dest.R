# EXPECTED: R042 at line 5
# EXPECTED: R042 at line 6

opt_list <- list(
  optparse::make_option("--band-lo", default = 0.22),
  optparse::make_option("--band-hi", default = 0.36),
  optparse::make_option("--seed",    default = 42L)
)
opt <- optparse::parse_args(optparse::OptionParser(option_list = opt_list))

# Only --seed is consumed.
set.seed(opt$seed)

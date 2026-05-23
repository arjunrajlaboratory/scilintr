schema <- list(band_lo = "numeric", band_hi = "numeric", fdr = "numeric")
cfg <- validate_config(yaml::read_yaml("analysis_config.yaml"), schema)
band_lo <- cfg$band_lo

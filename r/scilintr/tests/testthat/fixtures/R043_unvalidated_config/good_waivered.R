# ANALYSIS_OK[unvalidated-config]: this is a development-only sweep config;
# typos here should surface as NULLs (user errors), not safe defaults.
sweep_cfg <- yaml::read_yaml("sweep_grid.yaml")
band_lo_range <- sweep_cfg$band_lo

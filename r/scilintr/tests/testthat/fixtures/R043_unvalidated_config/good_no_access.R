# Config is loaded but only passed wholesale to another function; no
# per-key access happens in this file. The validation/extraction is
# someone else's problem.
cfg <- yaml::read_yaml("config.yaml")
run_pipeline(cfg)

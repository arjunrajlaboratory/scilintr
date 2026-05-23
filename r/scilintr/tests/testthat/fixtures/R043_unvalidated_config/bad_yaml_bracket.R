# EXPECTED: R043 at line 3

cfg <- yaml::yaml.load_file("config.yaml")
fdr <- cfg[["fdr_threshold"]]

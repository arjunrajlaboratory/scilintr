# STAGE: evaluation

# ANALYSIS_OK[label-tuned-threshold]: BAND is documented as label-tuned in
# analysis_constants.yml (is_label_tuned: true); evaluation-stage use is
# allowed by allowed_stages: [evaluation].
cfg <- yaml::read_yaml("analysis_constants.yml")
BAND <- cfg$band
sweep <- read.csv("output/gt17_band_sweep.csv")
panel <- panel_source[panel_source$vaf > BAND$lo & panel_source$vaf < BAND$hi, ]

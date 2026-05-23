# STAGE: selection

cfg <- yaml::read_yaml("analysis_constants.yml")
BAND <- cfg$band
panel <- panel_source[panel_source$vaf > BAND$lo & panel_source$vaf < BAND$hi, ]

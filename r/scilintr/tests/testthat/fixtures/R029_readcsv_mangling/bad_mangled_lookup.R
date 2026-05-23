# EXPECTED: R029 at line 5

# read.csv mangles "17-38733306C>T" to "X17.38733306C.T"
df <- read.csv("snp_panel.csv")
hit <- df[["17-38733306C>T"]]

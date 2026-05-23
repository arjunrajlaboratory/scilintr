# EXPECTED: R008 at line 4

files <- list.files("data/", pattern = "counts.*csv", full.names = TRUE)
path <- files[which.max(file.info(files)$mtime)]
counts <- read.csv(path)

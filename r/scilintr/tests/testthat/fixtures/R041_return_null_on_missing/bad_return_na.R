# EXPECTED: R041 at line 5

load_panel <- function(path) {
  if (!file.exists(path)) {
    return(NA)
  }
  read.csv(path)
}

# STAGE: evaluation

expr <- as.matrix(read.csv("expr.csv", row.names = 1))
metadata <- read.csv("metadata.csv")
pca_coords <- prcomp(expr)$x
# ANALYSIS_OK[label-annotation-only]: treatment used only for plot color
# after PCA coordinates are fixed.
plot_df <- data.frame(pca_coords, treatment = metadata$treatment)

# ANALYSIS_OK[layer]: default assay/layer is set globally in 01_load_data.R
# (assay = "RNA", layer = "counts"); reuse for consistency.
obj <- readRDS("obj.rds")
x <- Seurat::GetAssayData(obj)

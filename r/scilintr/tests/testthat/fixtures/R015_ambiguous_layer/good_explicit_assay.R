obj <- readRDS("obj.rds")
EXPRESSION_LAYER <- "counts"
x <- Seurat::GetAssayData(obj, assay = "RNA", layer = EXPRESSION_LAYER)

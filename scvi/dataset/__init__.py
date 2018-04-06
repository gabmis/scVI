from .cortex import CortexDataset
from .dataset import GeneExpressionDataset
from .synthetic import SyntheticDataset

__all__ = ["SyntheticDataset", "CortexDataset", "GeneExpressionDataset"]


def load_dataset(dataset_name):
    if dataset_name == "synthetic":
        gene_dataset = SyntheticDataset()
    elif dataset_name == "cortex":
        # Should run preprocess_cortex.py before running - Maybe do check here ?
        gene_dataset = CortexDataset()
    else:
        raise "No such dataset available"
    return gene_dataset

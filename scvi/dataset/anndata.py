from .dataset import GeneExpressionDataset
import anndata
import numpy as np
import os


class AnnDataset(GeneExpressionDataset):
    r"""Loads a `.h5ad` file .

    ``AnnDataset`` class supports loading `Anndata`_ object.

    Args:
        :filename: Name of the `.h5ad` file.
        :save_path: Save path of the dataset. Default: ``'data/'``.
        :url: Url of the remote dataset. Default: ``None``.
        :new_n_genes: Number of subsampled genes. Default: ``False``.
        :subset_genes: List of genes for subsampling. Default: ``None``.


    Examples:
        >>> # Loading a local dataset
        >>> local_ann_dataset = AnnDataset("TM_droplet_mat.h5ad", save_path = 'data/')

    .. _Anndata:
        http://anndata.readthedocs.io/en/latest/

    """

    def __init__(
        self,
        filename_or_anndata,
        save_path="data/",
        url=None,
        new_n_genes=False,
        subset_genes=None,
    ):
        """

        """

        if type(filename_or_anndata) == str:
            self.download_name = filename_or_anndata
            self.save_path = save_path
            self.url = url

            data, gene_names, batch_indices, cell_types, labels = (
                self.download_and_preprocess()
            )

        elif isinstance(filename_or_anndata, anndata.AnnData):
            ad = filename_or_anndata
            data, gene_names, batch_indices, cell_types, labels = self.extract_data_from_anndata(
                ad
            )

        else:
            raise Exception(
                "Please provide a filename of an AnnData file or an already loaded AnnData object"
            )

        X, local_means, local_vars, batch_indices_, labels = GeneExpressionDataset.get_attributes_from_matrix(
            data, labels=labels
        )
        batch_indices = batch_indices if batch_indices is not None else batch_indices_

        super().__init__(
            X,
            local_means,
            local_vars,
            batch_indices,
            labels,
            gene_names=gene_names,
            cell_types=cell_types,
        )

        self.subsample_genes(new_n_genes=new_n_genes, subset_genes=subset_genes)

    def preprocess(self):
        print("Preprocessing dataset")
        ad = anndata.read_h5ad(
            os.path.join(self.save_path, self.download_name)
        )  # obs = cells, var = genes
        data, gene_names, batch_indices, cell_types, labels = self.extract_data_from_anndata(
            ad
        )

        print("Finished preprocessing dataset")
        return data, gene_names, batch_indices, cell_types, labels

    def extract_data_from_anndata(self, ad: anndata.AnnData):
        data, gene_names, batch_indices, cell_types, labels = (
            None,
            None,
            None,
            None,
            None,
        )
        self.obs = (
            ad.obs
        )  # provide access to observation annotations from the underlying AnnData object.

        if isinstance(ad.X, np.ndarray):
            data = ad.X.copy()  # Dense
        else:
            data = ad.X.toarray()  # Sparse

        select = data.sum(axis=1) > 0  # Take out cells that doesn't express any gene
        data = data[select, :]

        gene_names = np.array(ad.var.index.values, dtype=str)

        if "batch_indices" in self.obs.columns:
            batch_indices = self.obs["batch_indices"].values

        if "cell_types" in self.obs.columns:
            cell_types = self.obs["cell_types"]
            cell_types = cell_types.drop_duplicates().values.astype("str")

        if "labels" in self.obs.columns:
            labels = self.obs["labels"]
        elif "cell_types" in self.obs.columns:
            labels = self.obs["cell_types"].rank(method="dense").values.astype("int")

        return data, gene_names, batch_indices, cell_types, labels

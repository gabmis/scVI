import collections
import time

import numpy as np
import scipy.sparse as sp_sparse
import tables

from .const import string_10x
from .dataset import GeneExpressionDataset

GeneBCMatrix = collections.namedtuple(
    "GeneBCMatrix", ["gene_ids", "gene_names", "barcodes", "matrix"]
)


def get_matrix_from_h5(filename, genome):
    with tables.open_file(filename, "r") as f:
        try:
            dsets = {}
            for node in f.walk_nodes("/" + genome, "Array"):
                dsets[node.name] = node.read()
            matrix = sp_sparse.csc_matrix(
                (dsets["data"], dsets["indices"], dsets["indptr"]), shape=dsets["shape"]
            )
            return GeneBCMatrix(
                dsets["genes"], dsets["gene_names"], dsets["barcodes"], matrix
            )
        except tables.NoSuchNodeError:
            raise Exception("Genome %s does not exist in this file." % genome)
        except KeyError:
            raise Exception("File is missing one or more required datasets.")


def subsample_barcodes(gbm, barcode_indices, unit_test=False):
    barcodes = gbm.barcodes[barcode_indices] if not unit_test else gbm.barcodes
    return GeneBCMatrix(
        gbm.gene_ids, gbm.gene_names, barcodes, gbm.matrix[:, barcode_indices]
    )


def subsample_genes(gbm, genes_indices, unit_test=False):
    gene_ids = gbm.gene_ids[genes_indices] if not unit_test else gbm.gene_ids
    gene_names = gbm.gene_names[genes_indices] if not unit_test else gbm.gene_names
    return GeneBCMatrix(
        gene_ids, gene_names, gbm.barcodes, gbm.matrix[genes_indices, :]
    )


def get_expression(gbm, gene_name):
    gene_indices = np.where(gbm.gene_names == gene_name)[0]
    if len(gene_indices) == 0:
        raise Exception("%s was not found in list of gene names." % gene_name)
    return gbm.matrix[gene_indices[0], :].toarray().squeeze()


class BrainLargeDataset(GeneExpressionDataset):
    url = "http://cf.10xgenomics.com/samples/cell-exp/1.3.0/1M_neurons/1M_neurons_filtered_gene_bc_matrices_h5.h5"

    def __init__(self, subsample_size=60000, unit_test=False, nb_genes_kept=720):
        """
        :param subsample_size: In thousands of barcodes kept (by default 1*1000=1000 kept)
        :param unit_test: A boolean to indicate if we use pytest subsampled file
        """
        self.subsample_size = subsample_size if not unit_test else 128
        self.save_path = "data/"
        self.unit_test = unit_test
        self.nb_genes_kept = nb_genes_kept
        # originally: "1M_neurons_filtered_gene_bc_matrices_h5.h5"

        if not self.unit_test:
            self.download_name = "genomics.h5"
        else:
            self.download_name = "../tests/data/genomics_subsampled.h5"

        self.genome = "mm10"
        if False:
            h5_object = self.download_and_preprocess()
            super(BrainLargeDataset, self).__init__(
                *GeneExpressionDataset.get_attributes_from_matrix(
                    h5_object.matrix.transpose().toarray()
                )
            )
        if True:  # Romain's preprocessing
            Xs = self.download_and_preprocess()
            super(BrainLargeDataset, self).__init__(
                *GeneExpressionDataset.get_attributes_from_list(Xs)
            )

    def preprocess(self):
        print("Preprocessing Brain Large data")
        tic = time.time()
        filtered_matrix_h5 = self.save_path + self.download_name
        gene_bc_matrix = get_matrix_from_h5(filtered_matrix_h5, self.genome)

        # Downsample from 1306127 to 100000 (~1/10) to get most variable genes
        matrix = gene_bc_matrix.matrix[:, :100000]
        variance = (
            np.array(matrix.multiply(matrix).mean(1)) - np.array(matrix.mean(1)) ** 2
        )[:, 0]
        mask_small = variance >= 1.912

        subsampled_matrix = subsample_genes(
            gene_bc_matrix, mask_small, unit_test=self.unit_test
        )
        print(subsampled_matrix.matrix.shape)  # 720 * ...

        if not self.unit_test:
            batch = [int(x[8:10]) - 9 for x in string_10x.split("\n")]
            batch_id = np.array(
                [batch[int(x.split(b"-")[-1]) - 1] for x in subsampled_matrix.barcodes]
            )
        else:
            batch_id = np.random.randint(0, 2, size=subsampled_matrix.matrix.T.shape[0])

        idx = np.random.permutation(len(batch_id))[: self.subsample_size]

        X = subsampled_matrix.matrix.T[idx]
        b = batch_id[idx]
        Xs = [X[b == batch].A for batch in (0, 1)]
        print(Xs[0].shape)
        toc = time.time()
        print("Preprocessing finished in : %d sec." % int(toc - tic))
        return Xs

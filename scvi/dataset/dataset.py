# -*- coding: utf-8 -*-

"""Handling datasets.
For the moment, is initialized with a torch Tensor of size (n_cells, nb_genes)"""
import numpy as np
import scipy.sparse as sp_sparse
import torch
from torch.utils.data import Dataset


class GeneExpressionDataset(Dataset):
    """Gene Expression dataset. It deals with:
    - log_variational expression -> torch.log(1 + X)
    - local library size normalization (mean, var) per batch
    """

    def __init__(
        self,
        X,
        local_means,
        local_vars,
        batch_indices,
        labels,
        gene_names=None,
        n_batches=1,
    ):
        # Args:
        # Xs: a list of numpy tensors with .shape[1] identical (total_size*nb_genes)
        # or a list of scipy CSR sparse matrix,
        # or transposed CSC sparse matrix (the argument sparse must then be set to true)
        self.total_size, self.nb_genes = X.shape
        self.n_batches = n_batches
        self.local_means = local_means
        self.local_vars = local_vars
        self.batch_indices = batch_indices
        self.X = X
        self.labels = labels

        if gene_names is not None:
            self.gene_names = np.char.upper(
                gene_names
            )  # Take an upper case convention for gene names

    def __len__(self):
        return self.total_size

    def __getitem__(self, idx):
        return (
            self.X[idx].toarray()[0],
            self.local_means[idx],
            self.local_vars[idx],
            self.batch_indices[idx],
            self.labels[idx],
        )

    @staticmethod
    def train_test_split(*Xs, train_size=0.75):
        """
        A substitute for the sklearn function to avoid the dependency
        """
        Xs = [np.array(X) for X in Xs]
        split_idx = int(train_size * len(Xs[0]))
        all_indices = np.arange(len(Xs[0]))
        train_indices = np.random.choice(all_indices, size=split_idx, replace=False)
        test_indices = np.array(list(set(all_indices).difference(set(train_indices))))
        split_list = [[X[train_indices], X[test_indices]] for X in Xs]
        return [X for Xs in split_list for X in Xs]

    @staticmethod
    def compute_attributes(X, batch_index=0):
        log_counts = torch.log(
            torch.from_numpy(np.asarray((X.sum(axis=1)), dtype=float)).type(
                torch.FloatTensor
            )
        )
        local_mean = torch.mean(log_counts) * torch.ones((X.shape[0], 1))
        local_var = torch.var(log_counts) * torch.ones((X.shape[0], 1))
        batch_index = torch.LongTensor(batch_index * np.ones((X.shape[0], 1)))
        return X, local_mean, local_var, batch_index

    @classmethod
    def from_list_batches(cls, Xs, list_labels=None, gene_names=None):
        nb_genes = Xs[0].shape[1]
        n_batches = len(Xs)
        assert all(
            X.shape[1] == nb_genes for X in Xs
        ), "All tensors must have same size"

        new_Xs = []
        local_means = []
        local_vars = []
        batch_indices = []
        for i, X in enumerate(Xs):
            X, local_mean, local_var, batch_index = GeneExpressionDataset.compute_attributes(
                X, batch_index=i
            )
            new_Xs += [X]
            local_means += [local_mean]
            local_vars += [local_var]
            batch_indices += [batch_index]
        local_means = torch.cat(local_means)
        local_vars = torch.cat(local_vars)
        batch_indices = torch.cat(batch_indices)

        if list_labels is not None:
            labels = []
            for labels in list_labels:
                labels += [torch.LongTensor(labels.reshape(-1, 1))]
            labels = torch.cat(labels, dim=0)
        else:
            labels = torch.zeros_like(batch_indices)

        X = sp_sparse.vstack(new_Xs)
        return cls(
            X,
            local_means,
            local_vars,
            batch_indices,
            labels,
            gene_names=gene_names,
            n_batches=n_batches,
        )

    @classmethod
    def from_matrix(cls, X, labels=None, gene_names=None):
        if labels is None:
            labels = torch.zeros(X.shape[0], 1).type(torch.LongTensor)
        return cls(
            *GeneExpressionDataset.compute_attributes(X),
            labels=labels,
            gene_names=gene_names
        )

    @classmethod
    def get_dataset(cls, **kargs):
        return cls.get_dataset(**kargs)

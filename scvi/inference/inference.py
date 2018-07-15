import sys
from collections import defaultdict

import torch
from tqdm import trange

from scvi.metrics.early_stopping import EarlyStopping
from scvi.utils import to_cuda, enable_grad


class Inference:
    """
    Inference class cares about the general training of a PyTorch model with its statistics
    """

    default_metrics_to_monitor = []

    def __init__(
        self,
        model,
        gene_dataset,
        use_cuda=True,
        metrics_to_monitor=None,
        data_loaders=None,
        benchmark=False,
        verbose=False,
        frequency=None,
        early_stopping_metric=None,
        save_best_state_metric=None,
        on=None,
    ):
        self.model = model
        self.gene_dataset = gene_dataset
        self.data_loaders = data_loaders
        self.benchmark = benchmark
        self.epoch = 0

        if metrics_to_monitor is not None:
            self.metrics_to_monitor = metrics_to_monitor
        else:
            self.metrics_to_monitor = self.default_metrics_to_monitor

        self.early_stopping_metric = early_stopping_metric
        self.save_best_state_metric = save_best_state_metric
        self.on = on
        mode = (
            getattr(self, early_stopping_metric).mode
            if early_stopping_metric is not None
            else None
        )
        mode_save_state = (
            getattr(self, save_best_state_metric).mode
            if save_best_state_metric is not None
            else None
        )
        self.early_stopping = EarlyStopping(
            benchmark=benchmark, mode=mode, mode_save_state=mode_save_state
        )

        self.use_cuda = use_cuda and torch.cuda.is_available()
        if self.use_cuda:
            self.model.cuda()

        self.frequency = frequency if not benchmark else None
        self.verbose = verbose

        self.history = defaultdict(lambda: [])

    def compute_metrics(self):
        if self.frequency and (
            self.epoch == 0
            or self.epoch == self.n_epochs
            or (self.epoch % self.frequency == 0)
        ):
            if self.verbose:
                print("\nEPOCH [%d/%d]: " % (self.epoch, self.n_epochs))
            for name in self.data_loaders.to_monitor:
                for metric in self.metrics_to_monitor:
                    result = getattr(self, metric)(name=name, verbose=self.verbose)
                    self.history[metric + "_" + name] += [result]

    @enable_grad()
    def fit(self, n_epochs=20, lr=1e-3):
        optimizer = (
            self.optimizer
            if hasattr(self, "optimizer")
            else torch.optim.Adam(
                filter(lambda p: p.requires_grad, self.model.parameters()), lr=lr
            )
        )
        self.epoch = 0
        self.n_epochs = n_epochs
        self.compute_metrics()
        with trange(
            n_epochs, desc="training", file=sys.stdout, disable=self.verbose
        ) as pbar:
            # We have to use tqdm this way so it works in Jupyter notebook.
            # See https://stackoverflow.com/questions/42212810/tqdm-in-jupyter-notebook
            self.on_epoch_begin()
            for epoch in pbar:
                pbar.update(1)
                for tensors_list in self.data_loaders:
                    loss = self.loss(
                        *[
                            to_cuda(tensors, use_cuda=self.use_cuda)
                            for tensors in tensors_list
                        ]
                    )
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                if not self.on_epoch_end():
                    break
        if self.save_best_state_metric is not None:
            self.model.load_state_dict(self.best_state_dict)
            self.compute_metrics()

    def on_epoch_begin(self):
        pass

    def on_epoch_end(self):
        self.epoch += 1
        self.compute_metrics()
        if self.save_best_state_metric is not None and self.on is not None:
            if self.early_stopping.update_state(
                self.history[self.save_best_state_metric + "_" + self.on][-1]
            ):
                self.best_state_dict = self.model.state_dict()
                self.best_epoch = self.epoch

        continue_training = True
        if self.early_stopping_metric is not None and self.on is not None:
            continue_training = self.early_stopping.update(
                self.history[self.early_stopping_metric + "_" + self.on][-1]
            )
        return continue_training

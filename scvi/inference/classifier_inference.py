from torch.nn import functional as F

from scvi.dataset.utils import TrainTestDataLoaders
from scvi.metrics.classification import compute_accuracy
from . import Inference


class ClassifierInference(Inference):
    default_metrics_to_monitor = ["accuracy"]
    baselines = ["svc_rf"]

    def __init__(self, *args, sampling_model=None, **kwargs):
        self.sampling_model = sampling_model
        super(ClassifierInference, self).__init__(*args, **kwargs)
        if "data_loaders" not in kwargs:
            self.data_loaders = TrainTestDataLoaders(
                self.gene_dataset, train_size=0.1, pin_memory=self.use_cuda
            )

    def fit(self, *args, **kargs):
        if hasattr(self.model, "update_parameters"):
            self.model.update_parameters(
                self.sampling_model, self.data_loaders["train"], use_cuda=self.use_cuda
            )
        else:
            super(ClassifierInference, self).fit(*args, **kargs)

    def loss(self, tensors_labelled):
        x, _, _, _, labels_train = tensors_labelled
        x = (
            self.sampling_model.sample_from_posterior_z(x)
            if self.sampling_model is not None
            else x
        )
        return F.cross_entropy(self.model(x), labels_train.view(-1))

    def accuracy(self, name, verbose=False):
        model, cls = (
            (self.sampling_model, self.model)
            if hasattr(self, "sampling_model")
            else (self.model, None)
        )
        acc = compute_accuracy(
            model, self.data_loaders[name], classifier=cls, use_cuda=self.use_cuda
        )
        if verbose:
            print("Acc for %s is : %.4f" % (name, acc))
        return acc

    accuracy.mode = "max"

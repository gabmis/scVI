import random

import numpy as np
import torch

from scvi.models.stats import Stats
from scvi.utils import to_cuda


def train(
    vae,
    data_loader_train,
    data_loader_test,
    n_epochs=20,
    learning_rate=0.001,
    kl=None,
    early_stopping_criterion=(20, 0.01),
    verbose=True,
    verbose_frequency=5,
):
    # Defining the optimizer
    optimizer = torch.optim.Adam(vae.parameters(), lr=learning_rate, eps=0.01)

    # initialize
    (patience, threshold) = (early_stopping_criterion[0], early_stopping_criterion[1])
    current_performances_kl = np.ones((patience))
    current_performances_reconst = np.ones((patience))

    # Getting access to the stats during training
    stats = Stats(verbose, verbose_frequency)

    # Training the model
    for epoch in range(n_epochs):
        # initialize kl, reconst
        total_current_kl = 0
        total_current_reconst = 0
        for i_batch, tensor_list in enumerate(data_loader_train):
            if vae.using_cuda:
                tensor_list = to_cuda(tensor_list)
            sample_batch, local_l_mean, local_l_var, batch_index, labels = tensor_list
            sample_batch = sample_batch.type(torch.float32)

            labels = labels if random.random() < 0.5 else None

            if kl is None:
                kl_ponderation = min(1, epoch / 400.0)
            else:
                kl_ponderation = kl

            reconst_loss, kl_divergence = vae(
                sample_batch,
                local_l_mean,
                local_l_var,
                batch_index=batch_index,
                y=labels,
            )

            reconst_loss_mean = torch.mean(reconst_loss)
            kl_divergence_mean = torch.mean(kl_divergence)
            train_loss = reconst_loss_mean + kl_ponderation * kl_divergence_mean

            batch_size = sample_batch.size(0)
            total_current_kl += kl_divergence_mean.item() * batch_size
            total_current_reconst += reconst_loss_mean.item() * batch_size

            optimizer.zero_grad()
            train_loss.backward()
            optimizer.step()

        current_performances_kl[:-1] = current_performances_kl[1:]
        current_performances_reconst[:-1] = current_performances_reconst[1:]
        current_performances_kl[-1] = total_current_kl / len(
            data_loader_train.sampler.indices
        )
        current_performances_reconst[-1] = total_current_reconst / len(
            data_loader_train.sampler.indices
        )

        # Computing the relative improvment of kl and reconstruction loss
        # over the chosen number of epochs
        reconst_relative_improvement = (
            current_performances_reconst[0] - current_performances_reconst[-1]
        ) / current_performances_reconst[0]
        kl_relative_improvement = (
            current_performances_kl[0] - current_performances_kl[-1]
        ) / current_performances_kl[0]
        # Test whether stopping criterions are met
        if (
            epoch > patience
            and kl_relative_improvement < threshold
            and reconst_relative_improvement < threshold
        ):
            # We then stop the iterations
            print(
                "Stopping the training after %d epochs: over the %d last epochs,"
                " kl divergence improvement was %.4f, reconstruction loss improvement was %.4f"
                % (
                    epoch,
                    patience,
                    kl_relative_improvement,
                    reconst_relative_improvement,
                )
            )
            return stats
            break

        stats.callback(vae, data_loader_train, data_loader_test)
    return stats

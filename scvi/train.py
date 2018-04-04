import numpy as np
import torch
from torch.autograd import Variable

import scvi.log_likelihood as lkl


def train(vae, data_loader, n_epochs=20):
    # Defining the optimizer
    optimizer = torch.optim.Adam(vae.parameters(), lr=0.0001)
    iter_per_epoch = len(data_loader)

    # Training the model
    for epoch in range(n_epochs):
        for i_batch, (sample_batched, local_l_mean, local_l_var) in enumerate(
            data_loader
        ):
            sample_batched = Variable(sample_batched, requires_grad=False)
            local_l_mean = Variable(
                local_l_mean.type(torch.FloatTensor), requires_grad=False
            )
            local_l_var = Variable(
                local_l_var.type(torch.FloatTensor), requires_grad=False
            )

            px_scale, px_r, px_rate, px_dropout, qz_m, qz_v, ql_m, ql_v = vae(
                sample_batched
            )

            approx = lkl.log_zinb_positive_approx(
                sample_batched, px_rate, torch.exp(px_r), px_dropout
            ).data[0]
            real = lkl.log_zinb_positive_real(
                sample_batched, px_rate, torch.exp(px_r), px_dropout
            ).data[0]
            delta = np.abs(approx - real)
            # Checking if the approximation for the log-likelihood is valid
            if delta > 1e-1:
                print("Error due to numerical approximation is: ", delta)

            # Computing the reconstruction loss

            reconst_loss = -lkl.log_zinb_positive_approx(
                sample_batched, px_rate, torch.exp(px_r), px_dropout
            )

            # Computing the kl divergence
            kl_divergence_z = torch.sum(
                0.5 * (qz_m ** 2 + qz_v - torch.log(qz_v + 1e-8) - 1), dim=-1
            )
            kl_divergence_l = torch.sum(
                0.5
                * (
                    ((ql_m - local_l_mean) ** 2) / local_l_var
                    + ql_v / local_l_var
                    + torch.log(local_l_var + 1e-8)
                    - torch.log(ql_v + 1e-8)
                    - 1
                ),
                dim=-1,
            )
            kl_divergence = kl_divergence_z + kl_divergence_l

            # Backprop + Optimize
            total_loss = torch.mean(reconst_loss + kl_divergence)
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

            # Simply printing the results
            if i_batch % 100 == 0 and epoch % 1 == 0:
                print(
                    "Epoch[%d/%d], Step [%d/%d], Total Loss: %.4f, "
                    "Reconst Loss: %.4f, KL Div: %.7f"
                    % (
                        epoch + 1,
                        20,
                        i_batch + 1,
                        iter_per_epoch,
                        total_loss.data[0],
                        reconst_loss.data[0],
                        kl_divergence.data[0],
                    )
                )

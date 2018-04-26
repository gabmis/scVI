import numpy as np
import torch

from scvi.utils import to_cuda


def imputation(vae, data_loader, rate=0.1):
    distance_list = torch.FloatTensor([])
    if vae.using_cuda:
        distance_list = distance_list.cuda(async=True)
    for tensorlist in data_loader:
        if vae.using_cuda:
            tensorlist = to_cuda(tensorlist)
        sample_batch, local_l_mean, local_l_var, batch_index, labels = tensorlist
        sample_batch = sample_batch.type(torch.float32)
        dropout_batch = sample_batch.clone()
        indices = torch.nonzero(dropout_batch)
        i, j = indices[:, 0], indices[:, 1]
        ix = torch.LongTensor(
            np.random.choice(range(len(i)), int(np.floor(rate * len(i))), replace=False)
        )
        dropout_batch[i[ix], j[ix]] *= 0

        if vae.using_cuda:
            ix, i, j = to_cuda([ix, i, j], async=False)
        px_rate = vae.get_sample_rate(dropout_batch, labels, batch_index=batch_index)
        distance_list = torch.cat(
            [
                distance_list,
                torch.abs(px_rate[i[ix], j[ix]] - sample_batch[i[ix], j[ix]]),
            ]
        )
    return torch.median(distance_list)

"""File for computing log likelihood of the data"""

import torch


def log_zinb_positive_real(x, mu, theta, pi, eps=1e-8):
    """
    Note: All inputs are torch Tensors
    log likelihood (scalar) of a minibatch according to a zinb model.
    Notes:
    We parametrize the bernoulli using the logits, hence the softplus functions appearing

    Variables:
    mu: mean of the negative binomial (has to be positive support) (shape: minibatch x genes)
    theta: inverse dispersion parameter (has to be positive support) (shape: minibatch x genes)
    pi: logit of the dropout parameter (real support) (shape: minibatch x genes)
    eps: numerical stability constant
    """
    case_zero = torch.log(
        torch.exp(
            (-pi + theta * torch.log(theta + eps) - theta * torch.log(theta + mu + eps))
        )
        + 1
    )
    -torch.log(torch.exp(-pi) + 1)

    case_non_zero = (
        -pi
        - torch.log(torch.exp(-pi) + 1)
        + theta * torch.log(theta + eps)
        - theta * torch.log(theta + mu + eps)
        + x * torch.log(mu + eps)
        - x * torch.log(theta + mu + eps)
        + torch.lgamma(x + theta)
        - torch.lgamma(theta)
        - torch.lgamma(x + 1)
    )

    mask = x.clone()
    mask[mask < eps] = 1
    mask[mask >= eps] = 0
    res = torch.mul(mask, case_zero) + torch.mul(1 - mask, case_non_zero)

    return torch.sum(res)


def log_zinb_positive_approx(x, mu, theta, pi, eps=1e-8):
    # CAREFUL: MODIFICATION WITH APPROXIMATION OF THE LGAMMA FUNCTION
    """
    Note: All inputs are torch Tensors
    log likelihood (scalar) of a minibatch according to a zinb model.
    Notes:
    We parametrize the bernoulli using the logits, hence the softplus functions appearing

    Variables:
    mu: mean of the negative binomial (has to be positive support) (shape: minibatch x genes)
    theta: inverse dispersion parameter (has to be positive support) (shape: minibatch x genes)
    pi: logit of the dropout parameter (real support) (shape: minibatch x genes)
    eps: numerical stability constant
    """
    case_zero = torch.log(
        torch.exp(
            (-pi + theta * torch.log(theta + eps) - theta * torch.log(theta + mu + eps))
        )
        + 1
    )
    -torch.log(torch.exp(-pi) + 1)

    case_non_zero = (
        -pi
        - torch.log(torch.exp(-pi) + 1)
        + theta * torch.log(theta + eps)
        - theta * torch.log(theta + mu + eps)
        + x * torch.log(mu + eps)
        - x * torch.log(theta + mu + eps)
        - torch.log(x + theta)
        + torch.log(theta + eps)
        + torch.log(x + 1)
    )

    mask = x.clone()
    mask[mask < eps] = 1
    mask[mask >= eps] = 0
    res = torch.mul(mask, case_zero) + torch.mul(1 - mask, case_non_zero)

    return torch.sum(res)


def log_nb_positive(x, mu, theta, eps=1e-8):
    """
    Note: All inputs should be torch Tensors
    log likelihood (scalar) of a minibatch according to a nb model.

    Variables:
    mu: mean of the negative binomial (has to be positive support) (shape: minibatch x genes)
    theta: inverse dispersion parameter (has to be positive support) (shape: minibatch x genes)
    eps: numerical stability constant
    """
    res = (
        theta * torch.log(theta + eps)
        - theta * torch.log(theta + mu + eps)
        + x * torch.log(mu + eps)
        - x * torch.log(theta + mu + eps)
        + torch.lgamma(x + theta)
        - torch.lgamma(theta)
        - torch.lgamma(x + 1)
    )
    return torch.sum(res)

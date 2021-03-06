"""Householder Normalizing Flow"""
import tensorflow as tf
from tensorflow.contrib import slim

from vary.flows.registry import RegisterFlow
from vary.flows.base import NormalizingFlow
from vary.flows.base import _VolumePreservingFlow

from vary.exceptions import GraphLookupError
from vary import tensor_utils as tensor_utils


class _HouseHolderFlow(_VolumePreservingFlow):
    def transform(self, z_sample, features=None):
        """Implements a single iteration of the Householder transformation.

        Parameters
        ----------
        z_sample : tensor of shape [batch_size, n_latent_dim]
            The sample generated from the previous iteration of the transformation.

        features : tensor of shape [batch_size, n_features]
            The input feature tensor used to construct the householder matrix.

        Returns
        -------
        z_new : tensor of shape [batch_size, n_latent_dim]
            Result of the transformation

        log_det_jacobian : tensor of shape [batch_size, 1]
            The logarithm of the deterimant of the jacobian of the
            transformation. The Householder flow is a volume preserving flow,
            so this is simply a vector of zeros.
        """
        with tf.variable_scope('householder_flow_single', [z_sample]):
            if features is None:
                raise ValueError('Householder flow requires a feature tensor.')

            z_sample = tensor_utils.to_tensor(z_sample, dtype=tf.float32)
            features = tensor_utils.to_tensor(features, dtype=tf.float32)
            n_latent_dim = tensor_utils.get_shape(z_sample)[1]

            v = slim.fully_connected(features,
                                     num_outputs=n_latent_dim,
                                     activation_fn=None)
            v_norm = tf.nn.l2_normalize(v, dim=[1])

            v_1 = tf.tile(tf.expand_dims(v_norm, 2), [1, 1, n_latent_dim])
            v_2 = tf.tile(tf.expand_dims(v_norm, 1), [1, n_latent_dim, 1])

            z_new = (z_sample -
                     tf.reduce_sum(
                        2 * (v_1 * v_2) * tf.expand_dims(z_sample, -1), 2))

            return z_new, self.log_det_jacobian(z_sample)


@RegisterFlow('householder')
class HouseHolderFlow(NormalizingFlow):
    """Implements the Householder Transformation, which is a
    valume-preserving normalizing flow. The purpose of narmalizing flows
    is to improve a VAE's evidence lower bound by performing a series
    of invertible transformations of latent variables with simple posteriors
    to generate a final random variable with a more flexible posterior.

    The evidence lower bound is given by

        E_q[ ln(p(x|z_T) + sum(ln(det(Jac(F)))) ] - KL(q(z_0|x)||p(z_T))

    where the sum is taken from t = 1 ... T and Jac(F) is the Jacobian
    matrix of the normalizing flow transformation wrt the latent variable.

    The householder transformation is a special normalizing flow that is also
    volume preserving, i.e. has zero Jacobian determinant. This means that
    performing this transformation results in a posterior with an
    (approximately) full-covariance matrix, while leaving the objective
    unmodified.

    Parameters
    ----------
    n_iter : int
        Number of iterations to perform the normalizing flow.

    random_state : int
        Seed to the random number generator

    Reference
    ---------
    - Jakub M. Tomczak and Max Welling,
      "Improving Variational Auto-Encoders using Householder Flow".
    """
    def __init__(self, n_iter=2, random_state=123):
        super(HouseHolderFlow, self).__init__(
            name='householder_flow',
            n_iter=n_iter,
            random_state=random_state)

    @property
    def flow_class(self):
        return _HouseHolderFlow

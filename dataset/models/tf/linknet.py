"""Contains class for LinkNet"""
import tensorflow as tf
import numpy as np

from .layers import conv_block
from . import TFModel


class LinkNet(TFModel):
    """ LinkNet
    https://arxiv.org/abs/1707.03718 (A.Chaurasia et al, 2017)

    **Configuration**
    -----------------
    inputs : dict
        dict with keys 'images' and 'masks' (see :meth:`._make_inputs`)
    batch_norm : bool
        if True enable batch normalization layers
    filters : int
        number of filters after the first convolution (64 by default)
    num_blocks : int
        number of downsampling/upsampling blocks (4 by default)
    """

    def _build(self):
        """ Builds a LinkNet model """
        names = ['images', 'masks']
        _, inputs = self._make_inputs(names)

        num_classes = self.num_classes('masks')
        data_format = self.data_format('images')
        dim = self.spatial_dim('images')
        enable_batch_norm = self.get_from_config('batch_norm', True)
        filters = self.get_from_config('filters', 64)
        num_blocks = self.get_from_config('num_blocks', 4)

        conv = {'data_format': data_format}

        kwargs = {'conv': conv, 'training': self.is_training}
        if enable_batch_norm:
            kwargs['batch_norm'] = {'momentum': 0.1}

        with tf.variable_scope('LinkNet'):
            layout = 'cpna' if enable_batch_norm else 'cpa'
            linknet_filters = 2 ** np.arange(num_blocks) * filters

            net = conv_block(dim, inputs['images'], filters, 7, layout, 'input_conv',
                             strides=2, pool_size=3, **kwargs)

            encoder_output = []
            for i, ifilters in enumerate(linknet_filters):
                net = self.downsampling_block(dim, net, ifilters, 'downsampling-'+str(i), **kwargs)
                encoder_output.append(net)

            for i, ifilters in enumerate(linknet_filters[::-1][1:]):
                net = self.upsampling_block(dim, net, ifilters, 'upsampling-'+str(i), **kwargs)
                net = tf.add(net, encoder_output[-2-i])
            net = self.upsampling_block(dim, net, filters, 'upsampling-'+str(i+1), **kwargs)

            layout = 'tnacnat' if enable_batch_norm else 'tacat'
            net = conv_block(dim, net, [32, 32, num_classes], [3, 3, 2], layout, 'output-conv',
                             strides=[2, 1, 2], **kwargs)

        logits = tf.identity(net, 'predictions')
        tf.nn.softmax(logits, name='predicted_proba')


    @staticmethod
    def downsampling_block(dim, inputs, filters, name, **kwargs):
        """LinkNet encoder block

        Parameters
        ----------
        dim : int
            spatial dimension of input without the number of channels
        inputs : tf.Tensor
        filters : int
            number of output filters
        name : str
            scope name

        Return
        ------
        outp : tf.Tensor
        """
        enable_batch_norm = 'batch_norm' in kwargs
        with tf.variable_scope(name):
            layout = 'cna' if enable_batch_norm else 'ca'
            net = conv_block(dim, inputs, filters, 3, 2*layout, 'conv-1', strides=[2, 1], **kwargs)
            shortcut = conv_block(dim, inputs, filters, 1, layout, 'conv-2', strides=2, **kwargs)
            add = tf.add(net, shortcut, 'add-1')

            net = conv_block(dim, add, filters, 3, 2*layout, 'conv-3', **kwargs)
            output = tf.add(net, add, 'add-2')
        return output

    @staticmethod
    def upsampling_block(dim, inputs, filters, name, **kwargs):
        """LinkNet decoder block

        Parameters
        ----------
        dim : int
            spatial dimension of input without the number of channels
        inputs : tf.Tensor
        filters : int
            number of output filters
        name : str
            scope name

        Return
        ------
        outp : tf.Tensor

        """
        enable_batch_norm = 'batch_norm' in kwargs
        with tf.variable_scope(name):
            layout = 'cnatnacna' if enable_batch_norm else 'cataca'
            num_filters = inputs.get_shape()[-1].value // 4

            output = conv_block(dim, inputs, [num_filters, num_filters, filters], [1, 3, 1],
                                layout, 'conv', strides=[1, 2, 1], **kwargs)
            return output
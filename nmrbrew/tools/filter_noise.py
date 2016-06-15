from .base import ToolBase
from ..ui import ConfigPanel
from ..globals import settings
from ..qt import *
from .. import utils


class FilterNoiseConfig(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(FilterNoiseConfig, self).__init__(*args, **kwargs)

        self.binsize_spin = QDoubleSpinBox()
        self.binsize_spin.setDecimals(3)
        self.binsize_spin.setRange(0.001, 0.5)
        self.binsize_spin.setSuffix('ppm')
        self.binsize_spin.setSingleStep(0.005)
        tl = QLabel(self.tr('Bin width'))
        self.layout.addWidget(tl)
        self.layout.addWidget(self.binsize_spin)
        self.config.add_handler('bin_size', self.binsize_spin)

        self.binoffset_spin = QDoubleSpinBox()
        self.binoffset_spin.setDecimals(3)
        self.binoffset_spin.setRange(-0.5, 0.5)
        self.binoffset_spin.setSuffix('ppm')
        self.binoffset_spin.setSingleStep(0.001)
        tl = QLabel(self.tr('Bin offset (start)'))
        self.layout.addWidget(tl)
        self.layout.addWidget(self.binoffset_spin)
        self.config.add_handler('bin_offset', self.binoffset_spin)

        self.finalise()


class FilterNoise(ToolBase):

    name = "Filter Noise"
    description = 'Remove noise from spectra'
    icon = 'filter_noise.png'

    def __init__(self, *args, **kwargs):
        super(FilterNoise, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })

        self.addConfigPanel(FilterNoiseConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run( self.noise )

    @staticmethod
    def noise(spc, config, progress_callback):
        import numpy as np
        import scipy as sp
        import scipy.signal
        import math

        def estimate_noise(s):

            h, w = s.shape

            m = [[1, -2, 1],
               [-2, 4, -2],
               [1, -2, 1]]

            sigma = np.sum(np.sum(np.absolute(sp.signal.convolve2d(s, m))))
            sigma = sigma * math.sqrt(0.5 * math.pi) / (6 * (w-2) * (h-2))

            return sigma

        noise = estimate_noise(spc.data)

        spc.data[ spc.data < noise ] = 0



        return {'spc':spc}

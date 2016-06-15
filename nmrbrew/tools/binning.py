from .base import ToolBase
from ..ui import ConfigPanel
from ..globals import settings
from ..qt import *
from .. import utils


class BinningConfig(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(BinningConfig, self).__init__(*args, **kwargs)

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


class Binning(ToolBase):

    name = "Spectral Binning"
    description = 'Reduce spectra resolution'
    icon = 'binning.png'

    def __init__(self, *args, **kwargs):
        super(Binning, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })

        self.addConfigPanel(BinningConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run( self.binning )

    @staticmethod
    def binning(spc, config, progress_callback):
        import numpy as np

        # Remove imaginaries
        spc.data = np.real(spc.data)

        scale = spc.ppm

        bin_size, bin_offset = config.get('bin_size'), config.get('bin_offset')

        r = min(scale), max(scale)

        bins = np.arange(r[0] + bin_offset, r[1] + bin_offset, bin_size)
        number_of_bins = len(bins) - 1

        # Can't increase the size of data, if bins > current size return the original
        if number_of_bins >= len(scale):
            pass

        else:

            input_data = spc.data
            input_data[ np.isnan(input_data) ] = 0
            spc.data = np.zeros((input_data.shape[0], number_of_bins))

            for n, d in enumerate(input_data):
                binned_data = np.histogram(scale, bins=bins, weights=d)
                binned_num = np.histogram(scale, bins=bins)  # Number of data points that ended up contributing to each bin
                spc.data[n, :] = binned_data[0]  # / binned_num[0]  # Mean

            new_scale = [float(x) for x in binned_data[1][:-1]]

            spc.ppm = np.array(new_scale)


        return {'spc':spc}

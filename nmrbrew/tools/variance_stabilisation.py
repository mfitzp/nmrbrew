from .base import ToolBase
from ..ui import ConfigPanel
from ..globals import settings
from ..qt import *
from .. import utils


class VarianceStabilisationConfig(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(VarianceStabilisationConfig, self).__init__(*args, **kwargs)

        self.algorithm = {
            'Autoscaling': 'autoscale',
            'gLog': 'glog',
            'Pareto': 'pareto',
            }

        self.gbs = {}

        vw = QVBoxLayout()
        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems([k for k, v in list(self.algorithm.items())])
        self.algorithm_cb.currentIndexChanged.connect(self.onSetAlgorithm)
        self.config.add_handler('algorithm', self.algorithm_cb, self.algorithm)
        vw.addWidget(self.algorithm_cb)  # ,0,0,1,2)        

        gb = QGroupBox('Algorithm')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        # Median  baseline settings
        #med_mw int
        #med_sf int
        #med_sigma float.0

        vw = QGridLayout()
        self.med_mw_spin = QSpinBox()
        self.med_mw_spin.setRange(1, 100)
        self.med_mw_spin.setSuffix('pts')
        self.config.add_handler('med_mw', self.med_mw_spin)
        tl = QLabel('Median window size')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.med_mw_spin, 0, 1)

        self.med_sf_spin = QSpinBox()
        self.med_sf_spin.setRange(1, 100)
        self.med_sf_spin.setSuffix('pts')
        self.config.add_handler('med_sf', self.med_sf_spin)
        tl = QLabel('Smooth window size')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.med_sf_spin, 1, 1)

        self.med_sigma_spin = QDoubleSpinBox()
        self.med_sigma_spin.setDecimals(1)
        self.med_sigma_spin.setRange(0.1, 10)
        self.med_sigma_spin.setSuffix('ppm')
        self.med_sigma_spin.setSingleStep(0.1)
        self.config.add_handler('med_sigma', self.med_sigma_spin)
        tl = QLabel('s.d. of Gaussian')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 2, 0)
        vw.addWidget(self.med_sigma_spin, 2, 1)

        gb = QGroupBox('Median baseline correction')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs['Median'] = gb
        # cbf settings
        #cbf_last_pc int

        vw = QGridLayout()
        self.cbf_last_pc_spin = QSpinBox()
        self.cbf_last_pc_spin.setRange(1, 100)
        self.cbf_last_pc_spin.setSuffix('%')
        self.config.add_handler('cbf_last_pc', self.cbf_last_pc_spin)
        tl = QLabel('Last n% of data')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.cbf_last_pc_spin, 0, 1)

        gb = QGroupBox('Constant from last % of spectra')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs['Constant from % of spectra'] = gb
        # cbf_explicit settings
        #cbf_explicit_start int
        #cbf_explicit_end int

        vw = QGridLayout()
        self.cbf_explicit_start_spin = QSpinBox()
        self.cbf_explicit_start_spin.setRange(1, 32767)
        self.config.add_handler('cbf_explicit_start', self.cbf_explicit_start_spin)

        self.cbf_explicit_end_spin = QSpinBox()
        self.cbf_explicit_end_spin.setRange(2, 32768)
        self.config.add_handler('cbf_explicit_end', self.cbf_explicit_end_spin)

        tl = QLabel('Start:end')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.cbf_explicit_start_spin, 0, 1)
        vw.addWidget(self.cbf_explicit_end_spin, 0, 2)

        gb = QGroupBox('Constant from explicit region')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs['Constant from start:end'] = gb
        # base settings
        #base_nl list of points
        #base_nw float.0

        self.onSetAlgorithm()
        self.finalise()

    def onSetAlgorithm(self):
        for k, v in list(self.gbs.items()):
            if self.algorithm_cb.currentText() == k:
                v.show()
            else:
                v.hide()


class VarianceStabilisation(ToolBase):

    name = "Variance stabilisation"
    description = "Apply glog or pareto transforms"
    icon = 'variance.png'

    def __init__(self, *args, **kwargs):
        super(VarianceStabilisation, self).__init__(*args, **kwargs)

        # Define default settings for pathway rendering
        self.config.set_defaults({
            # Peak target
            'algorithm': 'glog',
            # Baseline settings

        })

        self.addConfigPanel(VarianceStabilisationConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run(self.variance)


    @staticmethod
    def variance(spc, config, progress_callback):
        import numpy as np
        import scipy as sp

        algorithm = config.get('algorithm')
        if algorithm == 'glog':
            lam = 10**-13
            spc.data = np.log(spc.data + np.sqrt(spc.data** + lam))

        elif algorithm == 'autoscale':
            spc.data = spc.data / np.std(spc.data)

        elif algorithm == 'pareto':
            spc.data = spc.data / np.sqrt( np.std(spc.data) )

        # Clean up numeric extremities in data
        spc.data[np.isnan(spc.data)] = 0
        spc.data[np.isinf(spc.data)] = 0
        spc.data[np.isneginf(spc.data)] = 0

        return {'spc': spc}


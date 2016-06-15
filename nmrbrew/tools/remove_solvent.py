from .base import ToolBase
from ..ui import ConfigPanel
from ..globals import settings
from ..qt import *
from .. import utils


class RemoveSolventConfig(ConfigPanel):

    algorithm = {
        'Boxcar': 'boxcar',
        'Sine': 'sine',
        'Sine2': 'sine2',
        'Gaussian': 'gaussian',
        }

    def __init__(self, *args, **kwargs):
        super(RemoveSolventConfig, self).__init__(*args, **kwargs)

        vw = QVBoxLayout()
        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems([k for k, v in list(self.algorithm.items())])
        self.config.add_handler('algorithm', self.algorithm_cb, self.algorithm)
        vw.addWidget(self.algorithm_cb)  # ,0,0,1,2)

        gb = QGroupBox('Algorithm')
        gb.setLayout(vw)
        self.layout.addWidget(gb)


        self.finalise()



class RemoveSolvent(ToolBase):

    name = "Remove solvent"
    description = "Remove water from spectra"
    icon = 'solvent.png'

    def __init__(self, *args, **kwargs):
        super(RemoveSolvent, self).__init__(*args, **kwargs)

        # Define default settings for pathway rendering
        self.config.set_defaults({
            # Peak target
            'algorithm': 'sine2',
        })

        self.addConfigPanel(RemoveSolventConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run( self.solvent )


    @staticmethod
    def solvent(spc, config, progress_callback):
        import numpy as np
        import scipy as sp
        import nmrglue as ng

        fn = {
            'boxcar': ng.process.proc_bl.sol_boxcar,
            'sine': ng.process.proc_bl.sol_sine,
            'sine2': ng.process.proc_bl.sol_sine2,
            'gaussian': ng.process.proc_bl.sol_gaussian,
        }[config['algorithm']]

        def locate_nearest(array, value):
            idx = (np.abs(array-value)).argmin()
            return idx

        # Locate the water region by ppm 4.75..4.65
        start, end = locate_nearest(spc.ppm, 4.75), locate_nearest(spc.ppm, 4.65)
        print("Removing water from %d:%d" % (start, end ))
        spc.data[:,start:end] = fn(spc.data[:,start:end], w=16, mode='same')

        print(spc.data[start:end, :])

        return {'spc': spc}


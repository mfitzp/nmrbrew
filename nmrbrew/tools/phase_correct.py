from .base import ToolBase
from ..ui import ConfigPanel, QFolderLineEdit
from ..globals import settings
from ..qt import *


class PhaseCorrectConfig(ConfigPanel):

    autophase_algorithms = {
        'Peak minima': 'peak_minima',
        'ACME': 'acme',
    }

    def __init__(self, parent, *args, **kwargs):
        super(PhaseCorrectConfig, self).__init__(parent, *args, **kwargs)


        gb = QGroupBox('Automatic phase correction')
        gd = QGridLayout()

        cb_phasealg = QComboBox()
        cb_phasealg.addItems(self.autophase_algorithms.keys())
        gd.addWidget(QLabel('Algorithm'), 2, 0)
        gd.addWidget(cb_phasealg, 2, 1)
        self.config.add_handler('algorithm', cb_phasealg, self.autophase_algorithms)

        gb.setLayout(gd)
        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)


        gb = QGroupBox('Manual phase correction')
        gd = QGridLayout()
        gb.setLayout(gd)
        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)

        self.finalise()


class PhaseCorrect(ToolBase):

    name = "Phase correction"
    description = "Adjust p0 and p1 for spectra"
    icon = 'phase_correction.png'

    def __init__(self, *args, **kwargs):
        super(PhaseCorrect, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'algorithm': 'peak_minima',
        })

        self.addConfigPanel(PhaseCorrectConfig)
        self.addButtonBar(self.deftaultButtons())


    def run_manual(self):
        self.run( self.autophase )


    @staticmethod
    def autophase(spc, config, progress_callback):

        import nmrglue as ng
        import numpy as np
        import scipy as sp

        def autophase_ACME(x, s):
            # Based on the ACME algorithm by Chen Li et al. Journal of Magnetic Resonance 158 (2002) 164-168

            stepsize = 1

            n, l = s.shape
            phc0, phc1 = x

            s0 = ng.process.proc_base.ps(s, p0=phc0, p1=phc1)
            s = np.real(s0)
            maxs = np.max(s)

            # Calculation of first derivatives
            ds1 = np.abs((s[2:l] - s[0:l - 1]) / (stepsize * 2))
            p1 = ds1 / np.sum(ds1)

            # Calculation of entropy
            m, k = p1.shape

            for i in range(0, m):
                for j in range(0, k):
                    if (p1[i, j] == 0):  # %in case of ln(0)
                        p1[i, j] = 1

            h1 = -p1 * np.log(p1)
            h1s = np.sum(h1)

            # Calculation of penalty
            pfun = 0.0
            as_ = s - np.abs(s)
            sumas = np.sum(as_)

            if (sumas < 0):
                pfun = pfun + np.sum((as_ / 2) ** 2)

            p = 1000 * pfun

            # The value of objective function
            return h1s + p

        def autophase_PeakMinima(x, s):

            stepsize = 1

            phc0, phc1 = x

            s0 = ng.process.proc_base.ps(s, p0=phc0, p1=phc1)
            s = np.real(s0).flatten()

            i = np.argmax(s)
            peak = s[i]
            mina = np.min(s[i - 100:i])
            minb = np.min(s[i:i + 100])

            return np.abs(mina - minb)

        opt = [0, 0]
        fn = {
            'acme': autophase_ACME,
            'peak_minima': autophase_PeakMinima,
        }[config['algorithm']]

        for n, s in enumerate(spc.data):
            opt = sp.optimize.fmin(fn, x0=opt, args=(s.reshape(1, -1)[:500], ))
            print("Phase correction optimised to: %s" % opt)

            spc.data[n] = ng.process.proc_base.ps(s, p0=opt[0], p1=opt[1])
            progress_callback( float(n)/spc.data.shape[0] )

        return {'spc': spc}


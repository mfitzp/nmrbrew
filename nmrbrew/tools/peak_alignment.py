from .base import ToolBase
from ..ui import ConfigPanel, QFolderLineEdit
from ..globals import settings
from ..qt import *
from .. import utils

class PeakAlignmentConfig(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PeakAlignmentConfig, self).__init__(*args, **kwargs)

        self.peak_targets = {
            'TMSP': (0.0, 0.25),
            'Creatinine @4.0': (4.045, 0.25),
            'Creatinine @3.0': (3.030, 0.25),
            'Custom': (None, None),
        }

        vw = QGridLayout()
        self.peak_target_cb = QComboBox()
        self.peak_target_cb.addItems([k for k, v in list(self.peak_targets.items())])
        self.peak_target_cb.currentIndexChanged.connect(self.onSetPredefinedTarget)
        self.config.add_handler('peak_target', self.peak_target_cb)
        vw.addWidget(self.peak_target_cb, 0, 0, 1, 2)

        self.ppm_spin = QDoubleSpinBox()
        self.ppm_spin.setDecimals(2)
        self.ppm_spin.setRange(-1, 15)
        self.ppm_spin.setSuffix('ppm')
        self.ppm_spin.setSingleStep(0.05)
        self.ppm_spin.valueChanged.connect(self.onSetCustomTarget)  # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm', self.ppm_spin)
        vw.addWidget(self.ppm_spin, 1, 1, 1, 1)

        self.ppm_tolerance_spin = QDoubleSpinBox()
        self.ppm_tolerance_spin.setDecimals(2)
        self.ppm_tolerance_spin.setRange(0, 1)
        self.ppm_tolerance_spin.setSuffix('ppm')
        self.ppm_tolerance_spin.setSingleStep(0.05)
        self.ppm_tolerance_spin.valueChanged.connect(self.onSetCustomTarget)  # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm_tolerance', self.ppm_tolerance_spin)
        tl = QLabel('+/-')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 2, 0, 1, 1)
        vw.addWidget(self.ppm_tolerance_spin, 2, 1, 1, 1)

        gb = QGroupBox('Peak target')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        self.toggle_shift = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'icon.png')), 'Shift spectra', self.parent())
        self.toggle_shift.setCheckable(True)
        self.config.add_handler('shifting_enabled', self.toggle_shift)
        vw.addWidget(self.toggle_shift)

        self.toggle_scale = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'icon.png')), 'Scale spectra', self.parent())
        self.toggle_scale.setCheckable(True)
        self.config.add_handler('scaling_enabled', self.toggle_scale)
        vw.addWidget(self.toggle_scale)

        gb = QGroupBox('Toggle shift and scale')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        self.finalise()

    def onSetCustomTarget(self):
        if hasattr(self, '_automated_update_config') and self._automated_update_config is False:
            self.peak_target_cb.setCurrentText('Custom')

    def onSetPredefinedTarget(self):
        ppm, ppm_tol = self.peak_targets[self.peak_target_cb.currentText()]
        if ppm is not None:
            self._automated_update_config = True
            self.config.set('peak_target_ppm', ppm)
            self.config.set('peak_target_ppm_tolerance', ppm_tol)
            self._automated_update_config = False



class PeakAlignment(ToolBase):

    name = "Align to reference peak"
    description = "Align by peak (e.g. TMSP)"
    icon = 'peak_alignment.png'


    def __init__(self, *args, **kwargs):
        super(PeakAlignment, self).__init__(*args, **kwargs)

        # Define default settings for pathway rendering
        self.config.set_defaults({
            # Peak target
            'peak_target': 'TMSP',
            'peak_target_ppm': 0.0,
            'peak_target_ppm_tolerance': 0.5,
        })

        self.addConfigPanel(PeakAlignmentConfig)
        self.addButtonBar(self.deftaultButtons())


    def run_manual(self):
        self.run( self.shift )


    @staticmethod
    def shift(spc, config, progress_callback):

        import nmrglue as ng
        import numpy as np

        # Get the target region from the spectra (will be using this for all calculations;
        # then applying the result to the original data)

        # Remove imaginaries
        spc.data = np.real(spc.data)

        scale = spc.ppm

        target_ppm = config.get('peak_target_ppm')
        tolerance_ppm = config.get('peak_target_ppm_tolerance')
        start_ppm = target_ppm - tolerance_ppm
        end_ppm = target_ppm + tolerance_ppm

        start = min(list(range(len(scale))), key=lambda i: abs(scale[i]-start_ppm))
        end = min(list(range(len(scale))), key=lambda i: abs(scale[i]-end_ppm))

        # Shift first; then scale
        d = 1 if end>start else -1
        data = spc.data[:,start:end:d]
        region_scales = scale[start:end:d]

        pcentre = min(list(range(len(region_scales))), key=lambda i: abs(region_scales[i]-target_ppm))  # Base centre point to shift all spectra to


        reference_peaks = []
        for sdata in data:
            baseline = sdata.max() * .9 # 90% baseline of maximum peak within target region
            locations, scales, amps = ng.analysis.peakpick.pick(sdata, pthres=baseline, algorithm='connected', est_params = True, cluster=False, table=False)
            if len(locations) > 0:
                reference_peaks.append({
                    'location':locations[0][0], #FIXME: better behaviour when >1 peak
                    'scale':scales[0][0],
                    'amplitude':amps[0],
                })
            else:
                reference_peaks.append(None)

        # Take a np array for speed on shifting
        shift_array = spc.data
        # Now shift the original spectra to fi
        for n,refp in enumerate(reference_peaks):
            if refp:
                # Shift the spectra
                shift = (pcentre-refp['location']) * d
                # FIXME: This is painfully slow
                if shift > 0:
                    shift_array[n, shift:-1] = shift_array[n, 0:-(shift+1)]
                elif shift < 0:
                    shift_array[n, 0:shift-1] = shift_array[n, abs(shift):-1]

        spc.data = shift_array


        return {'spc': spc}

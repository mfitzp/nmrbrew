from ..qt import *
from ..ui import ConfigPanel
from .base import ToolBase


class PeakScalingConfig(ConfigPanel):
    def __init__(self, *args, **kwargs):
        super(PeakScalingConfig, self).__init__(*args, **kwargs)
        self._automated_update_config = False
        self.peak_targets = {
            "TMSP": (0.0, 0.25),
            "Creatinine @4.0": (4.045, 0.25),
            "Creatinine @3.0": (3.030, 0.25),
            "Custom": (None, None),
        }

        vw = QGridLayout()
        self.peak_target_cb = QComboBox()
        self.peak_target_cb.addItems([k for k, v in list(self.peak_targets.items())])
        self.peak_target_cb.currentIndexChanged.connect(self.onSetPredefinedTarget)
        self.config.add_handler("peak_target", self.peak_target_cb)
        vw.addWidget(self.peak_target_cb, 0, 0, 1, 2)

        self.ppm_spin = QDoubleSpinBox()
        self.ppm_spin.setDecimals(2)
        self.ppm_spin.setRange(-1, 15)
        self.ppm_spin.setSuffix("ppm")
        self.ppm_spin.setSingleStep(0.05)
        self.ppm_spin.valueChanged.connect(
            self.onSetCustomTarget
        )  # Additional; to handle alternation
        self.config.add_handler("peak_target_ppm", self.ppm_spin)
        vw.addWidget(self.ppm_spin, 1, 1, 1, 1)

        self.ppm_tolerance_spin = QDoubleSpinBox()
        self.ppm_tolerance_spin.setDecimals(2)
        self.ppm_tolerance_spin.setRange(0, 1)
        self.ppm_tolerance_spin.setSuffix("ppm")
        self.ppm_tolerance_spin.setSingleStep(0.05)
        self.ppm_tolerance_spin.valueChanged.connect(
            self.onSetCustomTarget
        )  # Additional; to handle alternation
        self.config.add_handler("peak_target_ppm_tolerance", self.ppm_tolerance_spin)
        tl = QLabel("+/-")
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 2, 0, 1, 1)
        vw.addWidget(self.ppm_tolerance_spin, 2, 1, 1, 1)

        gb = QGroupBox("Peak target")
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        self.finalise()

    def onSetCustomTarget(self):
        if self._automated_update_config is False:
            self.peak_target_cb.setCurrentText("Custom")

    def onSetPredefinedTarget(self):
        ppm, ppm_tol = self.peak_targets[self.peak_target_cb.currentText()]
        if ppm is not None:
            self._automated_update_config = True
            self.config.set("peak_target_ppm", ppm)
            self.config.set("peak_target_ppm_tolerance", ppm_tol)
            self._automated_update_config = False


class PeakScaling(ToolBase):
    name = "Scale to reference peak"
    description = "Scale by peak (e.g. TMSP)"
    icon = "peak_scaling.png"

    def __init__(self, *args, **kwargs):
        super(PeakScaling, self).__init__(*args, **kwargs)

        # Define default settings for pathway rendering
        self.config.set_defaults(
            {
                # Peak target
                "peak_target": "TMSP",
                "peak_target_ppm": 0.0,
                "peak_target_ppm_tolerance": 0.5,
            }
        )

        self.addConfigPanel(PeakScalingConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run(self.scale)

    @staticmethod
    def scale(spc, config, progress_callback):
        import nmrglue as ng
        import numpy as np

        # Get the target region from the spectra (will be using this for all calculations;
        # then applying the result to the original data)

        # Remove imaginaries
        spc.data = np.real(spc.data)

        scale = spc.ppm

        target_ppm = config.get("peak_target_ppm")
        tolerance_ppm = config.get("peak_target_ppm_tolerance")
        start_ppm = target_ppm - tolerance_ppm
        end_ppm = target_ppm + tolerance_ppm

        start = min(list(range(len(scale))), key=lambda i: abs(scale[i] - start_ppm))
        end = min(list(range(len(scale))), key=lambda i: abs(scale[i] - end_ppm))

        # Shift first; then scale
        d = 1 if end > start else -1
        data = spc.data[:, start:end:d]
        region_scales = scale[start:end:d]

        pcentre = min(
            list(range(len(region_scales))),
            key=lambda i: abs(region_scales[i] - target_ppm),
        )  # Base centre point to shift all spectra to

        reference_peaks = []
        for sdata in data:
            baseline = (
                sdata.max() * 0.9
            )  # 90% baseline of maximum peak within target region
            locations, scales, amps = ng.analysis.peakpick.pick(
                sdata,
                pthres=baseline,
                algorithm="connected",
                est_params=True,
                cluster=False,
                table=False,
            )
            if len(locations) > 0:
                reference_peaks.append(
                    {
                        "location": locations[0][
                            0
                        ],  # FIXME: better behaviour when >1 peak
                        "scale": scales[0][0],
                        "amplitude": amps[0],
                    }
                )
            else:
                reference_peaks.append(None)

        # Get mean reference peak size
        reference_peak_mean = np.mean([r["scale"] for r in reference_peaks if r])
        print("Reference peak mean %s" % reference_peak_mean)

        # Now scale; using the same peak regions & information (so we don't have to worry about something
        # being shifted out of the target region in the first step)
        for n, refp in enumerate(reference_peaks):
            if refp:
                # Scale the spectra
                amplitude = reference_peak_mean / refp["amplitude"]
                spc.data[n] *= amplitude

        return {"spc": spc}

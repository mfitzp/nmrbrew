import numpy as np

from ..qt import *
from ..ui import ConfigPanel
from .base import ToolBase


class BaselineCorrectionConfig(ConfigPanel):
    def __init__(self, *args, **kwargs):
        super(BaselineCorrectionConfig, self).__init__(*args, **kwargs)

        self.algorithm = {
            "Asymmetric Least Squares": "als",
            "Median": "median",
            #'Selected datapoints': 'base',
            "Constant from % of spectra": "cbf_pc",
            "Constant from start:end": "cbf_explicit",
        }

        self.gbs = {}

        vw = QVBoxLayout()
        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems([k for k, v in list(self.algorithm.items())])
        self.algorithm_cb.currentIndexChanged.connect(self.onSetAlgorithm)
        self.config.add_handler("algorithm", self.algorithm_cb, self.algorithm)
        vw.addWidget(self.algorithm_cb)  # ,0,0,1,2)

        gb = QGroupBox("Algorithm")
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        # Median  baseline settings
        # med_mw int
        # med_sf int
        # med_sigma float.0

        vw = QGridLayout()
        self.med_mw_spin = QSpinBox()
        self.med_mw_spin.setRange(1, 100)
        self.med_mw_spin.setSuffix("pts")
        self.config.add_handler("med_mw", self.med_mw_spin)
        tl = QLabel("Median window size")
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.med_mw_spin, 0, 1)

        self.med_sf_spin = QSpinBox()
        self.med_sf_spin.setRange(1, 100)
        self.med_sf_spin.setSuffix("pts")
        self.config.add_handler("med_sf", self.med_sf_spin)
        tl = QLabel("Smooth window size")
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.med_sf_spin, 1, 1)

        self.med_sigma_spin = QDoubleSpinBox()
        self.med_sigma_spin.setDecimals(1)
        self.med_sigma_spin.setRange(0.1, 10)
        self.med_sigma_spin.setSuffix("ppm")
        self.med_sigma_spin.setSingleStep(0.1)
        self.config.add_handler("med_sigma", self.med_sigma_spin)
        tl = QLabel("s.d. of Gaussian")
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 2, 0)
        vw.addWidget(self.med_sigma_spin, 2, 1)

        gb = QGroupBox("Median baseline correction")
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs["Median"] = gb
        # cbf settings
        # cbf_last_pc int

        vw = QGridLayout()
        self.cbf_last_pc_spin = QSpinBox()
        self.cbf_last_pc_spin.setRange(1, 100)
        self.cbf_last_pc_spin.setSuffix("%")
        self.config.add_handler("cbf_last_pc", self.cbf_last_pc_spin)
        tl = QLabel("Last n% of data")
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.cbf_last_pc_spin, 0, 1)

        gb = QGroupBox("Constant from last % of spectra")
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs["Constant from % of spectra"] = gb
        # cbf_explicit settings
        # cbf_explicit_start int
        # cbf_explicit_end int

        vw = QGridLayout()
        self.cbf_explicit_start_spin = QSpinBox()
        self.cbf_explicit_start_spin.setRange(1, 32767)
        self.config.add_handler("cbf_explicit_start", self.cbf_explicit_start_spin)

        self.cbf_explicit_end_spin = QSpinBox()
        self.cbf_explicit_end_spin.setRange(2, 32768)
        self.config.add_handler("cbf_explicit_end", self.cbf_explicit_end_spin)

        tl = QLabel("Start:end")
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.cbf_explicit_start_spin, 0, 1)
        vw.addWidget(self.cbf_explicit_end_spin, 0, 2)

        gb = QGroupBox("Constant from explicit region")
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs["Constant from start:end"] = gb
        # base settings
        # base_nl list of points
        # base_nw float.0

        self.onSetAlgorithm()
        self.finalise()

    def onSetAlgorithm(self):
        for k, v in list(self.gbs.items()):
            if self.algorithm_cb.currentText() == k:
                v.show()
            else:
                v.hide()


class BaselineCorrection(ToolBase):
    name = "Baseline correction"
    description = "Baseline correct NMR spectra"
    icon = "baseline.png"

    def __init__(self, *args, **kwargs):
        super(BaselineCorrection, self).__init__(*args, **kwargs)

        # Define default settings for pathway rendering
        self.config.set_defaults(
            {
                # Peak target
                "algorithm": "als",
                # Baseline settings
                "med_mw": 24,
                "med_sf": 16,
                "med_sigma": 5.0,
                # cbf settings
                "cbf_last_pc": 10,
                # cbf_explicit settings
                "cbf_explicit_start": 0,
                "cbf_explicit_end": 100,
                # base settings
                "base_nl": [],
                "base_nw": 0,
            }
        )

        self.addConfigPanel(BaselineCorrectionConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run(self.baseline)

    @staticmethod
    def baseline(spc, config, progress_callback):
        import numpy as np
        import scipy as sp
        import scipy.signal
        import scipy.sparse.linalg

        def baseline_als(y, lam, p, niter=10):
            L = len(y)
            D = sp.sparse.csc_matrix(np.diff(np.eye(L), 2))
            w = np.ones(L)

            for i in range(niter):
                W = sp.sparse.spdiags(w, 0, L, L)
                Z = W + lam * D.dot(D.transpose())
                z = sp.sparse.linalg.spsolve(Z, w * y)
                w = p * (y > z) + (1 - p) * (y < z)

            return z

        import nmrglue as ng

        algorithm = config.get("algorithm")

        # Medium algorithm vars
        med_mw = config.get("med_mw")
        med_sf = config.get("med_sf")
        med_sigma = config.get("med_sigma")

        # Cbf pc algorithm vars
        cbf_last_pc = config.get("cbf_last_pc")

        # Cbf explicit algorithm vars
        cbf_explicit_start = config.get("cbf_explicit_start")
        cbf_explicit_end = config.get("cbf_explicit_start")

        total_n = spc.data.shape[0]

        # Remove imaginaries
        spc.data = np.real(spc.data)
        bls = []
        bls_points = []

        # Calculate points for ALS
        if algorithm == "als":
            # FIXME: This should be
            point_step_size = 256
            # Find the indices of the smallest values in the sum of all spectra
            idx = np.arange(0, spc.data.shape[1], point_step_size)

            # Skip water region
            def locate_nearest(array, value):
                idx = (np.abs(array - value)).argmin()
                return idx

            start_idx = locate_nearest(spc.ppm, 4.5)
            end_idx = locate_nearest(spc.ppm, 5)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            print(idx, start_idx, end_idx)

            MASK_UP = idx > end_idx
            MASK_DOWN = idx < start_idx
            idx = idx[MASK_UP | MASK_DOWN]

            print(idx)

        for n, di in enumerate(spc.data):
            if algorithm == "median":
                dr = ng.process.proc_bl.med(di, mw=med_mw, sf=med_sf, sigma=med_sigma)

            elif algorithm == "cbf_pc":
                dr = ng.process.proc_bl.cbf(di, last=cbf_last_pc)

            elif algorithm == "cbf_explicit":
                dr = ng.process.proc_bl.cbf_explicit(
                    di, calc=slice(cbf_explicit_start, cbf_explicit_end)
                )

            elif algorithm == "als":
                # Find n minima in the spectra; using 0.05 threshold + filtering to step size 64
                bl = baseline_als(di[idx], lam=10**5, p=0.01)
                bls_points.append(bl)
                # Interpolate the line back to the correct size using spline function
                tck = sp.interpolate.splrep(spc.ppm[idx][::-1], bl[::-1], s=0)
                bl = sp.interpolate.splev(spc.ppm, tck, der=0)

                # fn = sp.interpolate.interp1d(spc.ppm[idx], bl, kind='slinear', bounds_error=False)
                # bl = fn(spc.ppm)
                dr = di - bl
                bls.append(bl)  # For visualisation

            spc.data[n, :] = dr

            progress_callback(float(n) / total_n)

        print(np.mean(np.array(bls_points), axis=0))
        return {
            "spc": spc,
            "baseline": np.array(bls),
            "baseline_point_idx": idx,
            "baseline_point_y": np.mean(np.array(bls_points), axis=0),
        }

    def plot(self, **kwargs):
        super(BaselineCorrection, self).plot(**kwargs)

        if "baseline" in self.data:
            canvas = self.parent().spectraViewer.spectraViewer
            pen = QPen(QColor(0, 0, 255, 100))
            pen.setWidth(0)
            for n, spc in enumerate(self.data["baseline"]):
                canvas.plot(self.data["spc"].ppm, spc, pen=pen)

        if (
            "baseline_point_idx" in self.data
            and self.data["baseline_point_idx"] is not None
        ):
            idx = self.data["baseline_point_idx"]
            canvas = self.parent().spectraViewer.spectraViewer

            mean_spc = np.mean(self.data["spc"].data, axis=0)
            canvas.plot(
                self.data["spc"].ppm[idx],
                self.data["baseline_point_y"],
                pen=None,
                symbol="o",
                symbolBrush=QBrush(QColor("blue")),
            )

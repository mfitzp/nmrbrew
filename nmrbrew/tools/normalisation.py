from .base import ToolBase
from ..ui import ConfigPanel
from ..globals import settings
from ..qt import *
from .. import utils

# Dialog box for Metabohunter search options
class NormalisationConfig(ConfigPanel):

    algorithms = ['PQN', 'TSA']

    def __init__(self, *args, **kwargs):
        super(NormalisationConfig, self).__init__(*args, **kwargs)

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems(self.algorithms)
        self.config.add_handler('algorithm', self.algorithm_cb)

        tl = QLabel('Scaling algorithm')
        tl.setIndent(5)
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)

        self.finalise()


class Normalisation(ToolBase):

    name = "Spectra normalisation"
    description = 'Normalise with TSA or PQN'
    notebook = 'spectra_norm.ipynb'
    icon = 'normalisation.png'

    def __init__(self, *args, **kwargs):
        super(Normalisation, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'algorithm': 'PQN',
        })

        self.addConfigPanel(NormalisationConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run( self.normalise )


    @staticmethod
    def normalise(spc, config, progress_callback):

        import numpy as np
        import pandas as pd

        # Remove imaginaries
        spc.data = np.real(spc.data)

        # Abs the data (so account for negative peaks also)
        data_a = np.abs(spc.data)
        # Sum each spectra (TSA)
        data_as = np.sum(data_a, axis=1)
        # Identify median
        median_s = np.median(data_as)
        # Scale others to match (*(median/row))
        scaling = median_s / data_as
        # Scale the spectra
        tsa_data = spc.data.T * scaling
        tsa_data = tsa_data.T

        if config['algorithm'] == 'TSA':
            output_data = tsa_data

        elif config['algorithm'] == 'PQN':
            # Take result of TSA normalization
            # Calculate median spectrum (median of each variable)
            median_s = np.median(tsa_data, axis=0)
            # For each variable of each spectrum, calculate ratio between median spectrum variable and that of the considered spectrum
            spectra_r = median_s / np.abs(spc.data)
            # Take the median of these scaling factors
            scaling = np.median(spectra_r, axis=1)
            #Apply to the entire considered spectrum
            output_data = spc.data.T * scaling
            spc.data = output_data.T

        # Clean up numeric extremities in data
        spc.data[np.isnan(spc.data)] = 0
        spc.data[np.isinf(spc.data)] = 0
        spc.data[np.isneginf(spc.data)] = 0

        return {'spc':spc}

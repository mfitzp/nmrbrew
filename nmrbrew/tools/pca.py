from .base import ToolBase
from ..ui import ConfigPanel, QFolderLineEdit, QNoneDoubleSpinBox
from ..globals import settings, config, SPECTRUM_COLOR, OUTLIER_COLOR, CLASS_COLORS
from ..qt import *

import numpy as np

from collections import defaultdict


# Dialog box for Metabohunter search options
class PCAConfig(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PCAConfig, self).__init__(*args, **kwargs)
        self.finalise()


class PCA(ToolBase):

    name = "PCA"
    description = "Principal component analysis"
    shortname = 'pca'
    icon = 'pca.png'

    config_panel_size = 50
    view_widget = 'PCAViewer'

    def __init__(self, *args, **kwargs):
        super(PCA, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            #'number_of_components': 2,
        })

        self.addConfigPanel(PCAConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run( self.pca )

    def activate(self):
        super(PCA, self).activate()
        self.parent().viewStack.setCurrentWidget(self.parent().pcaViewer)

    @staticmethod
    def pca(spc, config, progress_callback):
        from sklearn.decomposition import PCA

        number_of_components = 2 # No way to view > 2

        pca = PCA(n_components=number_of_components)
        pca.fit(spc.data)

        pca = {
            'scores': pca.transform(spc.data),
            'weights': pca.components_
        }

        return {'spc': spc, 'pca': pca}

    def plot(self, autofit=True, **kwargs):
        if 'spc' in self.data and 'pca' in self.data:
            self.parent().pcaViewer.plot(self.data['spc'], self.data['pca'], autofit=True, **kwargs)

    def get_plotitem(self):
        return self.parent().pcaViewer.pcaViewer.plotItem



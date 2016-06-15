from .base import ToolBase
from ..ui import ConfigPanel, QFolderLineEdit
from ..globals import settings
from ..qt import *
from .. import utils

class ExportSpectraConfig(ConfigPanel):

    pass

class ExportSpectra(ToolBase):

    name = "Export spectra"
    description = "Export processed spectra"
    icon = 'export.png'

    is_manual_runnable = False
    is_auto_runnable = False
    is_auto_rerunnable = False
    is_disableable = False

    def __init__(self, *args, **kwargs):
        super(ExportSpectra, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': '',
            'format': 'csv',

            'include_ppm': True,

            'include_labels': True,
            'include_classes': True,

            'transpose': False,
        })

        self.addConfigPanel(ExportSpectraConfig)

        export_csv = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'export.png')), 'Export to file')
        export_csv.setToolTip('Export spectra data')
        export_csv.pressed.connect(self.onExport)

        self.addButtonBar( [export_csv] )

    def onExport(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getSaveFileName(self.parent(), 'Export to file', os.path.expanduser("~"), filter="All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv)")
        print(filename)
        if filename:
            self.config.set('filename', filename)
            self.config.set('format', os.path.splitext(filename)[1])
            self.run( self.export )

    @staticmethod
    def export(spc, config, progress_callback):
        import numpy as np

        if config['format'] in ['.tsv', '.txt']:
            delimiter = '\t'
        else:
            delimiter = ','

        out = np.vstack([spc.ppm, spc.data])

        np.savetxt(config.get('filename'), out, delimiter=delimiter)

        return {'spc': spc}

    def activate(self):
        # Auto-import to output; we don't do anything
        self.data['spc'] = self.get_previous_spc()
        super(ExportSpectra, self).activate()

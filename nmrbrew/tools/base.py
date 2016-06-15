from ..qt import *
from .. import utils
from pyqtconfig import ConfigManager
import logging
from ..threads import Worker
from ..globals import custom_pyqtconfig_hooks

import numpy as np

from copy import deepcopy

SPECTRUM_COLOR = QColor(0, 0, 0, 100)

''' Brewer colors for spectra labelled by class '''
CLASS_COLORS = [
    QColor(31, 119, 180, 100),
    QColor(255, 127, 14, 100),
    QColor(44, 160, 44, 100),
    QColor(148, 103, 189, 100),
    QColor(140, 86, 75, 100),
    QColor(227, 119, 194, 100),
    QColor(127, 127, 127, 100),
    QColor(188, 189, 34, 100),
    QColor(23, 190, 207),
]



class ToolBase(QObject):
    '''
    Base tool definition for inclusion in the UI. Define specific config settings;
    attach a panel widget for configuration.
    '''

    is_manual_runnable = True

    is_auto_runnable = True
    is_auto_rerunnable = True
    is_disableable = True

    progress = pyqtSignal(float)
    status = pyqtSignal(str)

    config_panel_size = 250
    view_widget = 'SpectraViewer'

    def __init__(self, parent, *args, **kwargs):
        super(ToolBase, self).__init__(parent, *args, **kwargs)

        self.config = ConfigManager()
        self.config.hooks.update(custom_pyqtconfig_hooks.items())
        self.config.set_defaults({
            'is_active': True,
            'auto_run_on_config_change': True
            })

        self.config.updated.connect(self.auto_run_on_config_change)

        self.buttonBar = QWidget()

        self.configPanels = QWidget()
        self.configLayout = QVBoxLayout()
        self.configLayout.setContentsMargins(0,0,0,0)

        self.configPanels.setLayout(self.configLayout)

        self._previous_config_backup_ = {}

        self._worker_thread_ = None
        self._worker_thread_lock_ = False

        self.data = {
            'spc': None,

        }

        self.current_status = 'ready'
        self.current_progress = 0

        self.progress.connect(self.progress_callback)
        self.status.connect(self.status_callback)

    def addConfigPanel(self, panel):
        self.configLayout.addWidget( panel(self) )

    def addButtonBar(self, buttons):
        '''
        Create a button bar

        Supplied with a list of QPushButton objects (already created using helper stubs; see below)

        :param buttons:
        :return:
        '''

        btnlayout = QHBoxLayout()
        btnlayout.addSpacerItem(QSpacerItem(250, 1, QSizePolicy.Maximum, QSizePolicy.Maximum))
        for btn in buttons:
            btnlayout.addWidget(btn)

        self.configLayout.addLayout(btnlayout)
        btnlayout.addSpacerItem(QSpacerItem(250, 1, QSizePolicy.Maximum, QSizePolicy.Maximum))

    def run_manual(self):
        pass


    def disable(self):
        self.status.emit('inactive')
        self.config.set('is_active', False)
        self.item.setFlags(Qt.NoItemFlags)

    def reset(self):
        self.config.set_many( self.config.defaults )

    def undo(self):
        self.config.set_many(self._config_backup_)

    def deftaultButtons(self):

        buttons = []

        if self.is_disableable:
            disable = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'cross.png')), 'Disable')
            disable.setToolTip('Disable this tool')
            disable.pressed.connect(self.disable)
            buttons.append(disable)

        reset = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'arrow-turn-180-left.png')), 'Reset to defaults')
        reset.setToolTip('Reset to defaults')
        reset.pressed.connect(self.reset)
        buttons.append(reset)

        undo = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'arrow-turn-180-left.png')), 'Undo')
        undo.setToolTip('Undo recent changes')
        undo.pressed.connect(self.undo)
        buttons.append(undo)

        if self.is_auto_runnable:
            auto = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'lightning.png')), 'Auto')
            auto.setToolTip('Auto-update spectra when settings change')
            auto.setCheckable(True)
            auto.pressed.connect(self.run_manual)
            self.config.add_handler('auto_run_on_config_change', auto)
            buttons.append(auto)

        if self.is_manual_runnable:
            apply = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'play.png')), 'Apply')
            apply.setToolTip('Apply current settings to spectra')
            apply.pressed.connect(self.run_manual)
            buttons.append(apply)

        return buttons

    def enable(self):
        if self.current_status == 'inactive':
            self.status.emit('ready')
            self.item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        self.config.set('is_active', True)


    def activate(self):
        self.parent().current_tool = self
        self.enable()

        self._config_backup_ = self.config.as_dict()

        self._refresh_plot_timer_ = QTimer.singleShot(0, self.plot)

        self.parent().viewStack.setCurrentWidget(self.parent().spectraViewer)

        self.parent().configstack.setCurrentWidget(self.configPanels)
        self.parent().configstack.setMaximumHeight(self.config_panel_size)

    def set_active(self, active):
        self.config.set('is_active', active)

    def get_previous_tool(self):
        # Get the previous ACTIVE tool in the tool table
        n = self.parent().tools.index(self)
        for tool in self.parent().tools[n-1::-1]:
            if tool.current_status != 'inactive':
                return tool

        else:
            return None


    def get_previous_spc(self):
        t = self.get_previous_tool()
        if t:
            return t.data['spc']
        else:
            return None

    def plot(self, **kwargs):
        if 'spc' in self.data:
            self.parent().spectraViewer.plot(self.data['spc'], **kwargs)

    def get_plotitem(self):
        return self.parent().spectraViewer.spectraViewer.plotItem

    def auto_run_on_config_change(self):
        pass
        #if self.is_auto_runnable and self.config.get('is_active') and self.config.get('auto_run_on_config_change'):
        #    self.run_manual()

    def run(self, fn):
        '''
        Run the target function, passing in the current spectra, and config settings (as dict)
        :param fn:
        :return:
        '''
        if self._worker_thread_lock_:
            return False # Can't run

        self.progress.emit(0)
        self.status.emit('active')

        spc = self.get_previous_spc()

        self._worker_thread_lock_ = True

        print(self.config.as_dict())
        self._worker_thread_ = Worker(fn = fn, **{
            'spc': deepcopy(spc),
            'config': self.config.as_dict(),
            'progress_callback': self.progress.emit,
        })

        self._worker_thread_.signals.finished.connect(self.finished)
        self._worker_thread_.signals.result.connect(self.result)
        self._worker_thread_.signals.error.connect(self.error)

        self.parent().threadpool.start(self._worker_thread_)


    def error(self, error):
        self.progress.emit(1.0)
        self.status.emit('error')
        logging.error(error)
        self._worker_thread_lock_ = False

    def result(self, result):
        self.progress.emit(1)
        self.status.emit('complete')

        # Apply post-processing
        if 'spc' in result:
            result['spc'] = self.post_process_spc(result['spc'])

        self.data = result
        self.plot()

    def finished(self):
        # Cleanup
        self._worker_thread_lock_ = False


    def progress_callback(self, progress):
        self.current_progress = progress
        self.item.setData(Qt.UserRole + 2, progress)

    def status_callback(self, status):
        self.current_status = status
        self.item.setData(Qt.UserRole + 3, status)

    def post_process_spc(self, spc):
        '''
        Apply post-processing to the spectra before loading into the data store, e.g. for outlier
        detection, stats etc.

        :param spc:
        :return:
        '''

        # Outliers

        def identify_outliers(data, m=2):
            return abs(data - np.mean(data, axis=0)) < (m * np.std(data,axis=0))

        # Identify outliers on a point by point basis. Count up 'outliers' and score ratio of points that are
        # outliers for each specra > 5% (make this configurable) is an outlier.
        spc.outliers = np.sum( ~identify_outliers(spc.data), axis=1 ) / float(spc.data.shape[1])
        return spc

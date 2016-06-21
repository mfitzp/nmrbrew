# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import logging
import json
import datetime as dt
from copy import deepcopy

frozen = getattr(sys, 'frozen', False)
ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

# Used to enforce Qt version via matplotlib, etc.
os.environ['QT_API'] = 'pyqt5'

if sys.platform == 'win32' and sys.executable.split('\\')[-1] == 'pythonw.exe':
    # Dump all output when running without a console; otherwise will hang
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    frozen = True

elif sys.version_info < (3, 0) and ON_RTD is False:  # Python 2 only; unicode output fixes
    import codecs
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    reload(sys).setdefaultencoding('utf8')

if frozen:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

from .qt import *

import time
import requests

from .globals import settings, config

from . import ui
from . import utils
from . import spectra

# Translation (@default context)
from .translate import tr

from distutils.version import StrictVersion

import pyqtgraph as pg
import pyqtgraph.exporters

pg.setConfigOption('background', 'w')

__version__ = open(os.path.join(utils.basedir, 'VERSION'), 'rU').read()

from . import tools
from .tools import ( import_spectra, remove_solvent, phase_correct, 
    peak_alignment, baseline_correction,
    peak_scaling, exclude_regions, 
    #delete_imaginaries, filter, 
    icoshift_, filter_noise,
    binning, compress_bins, normalisation, variance_stabilisation, pca, export_spectra 
    )


   


class MainWindow(QMainWindow):

    updated = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        # Do version upgrade availability check
        # FIXME: Do check for new download here; if not done > 1 weeks
        if settings.get('core/last_checked') and settings.get('core/last_checked') < (int(time.time()) - 604800):  # 1 week in seconds
            try:
                r = requests.get('https://raw.githubusercontent.com/mfitzp/nmrbrew/master/VERSION')
            except:
                pass

            else:
                if r.status_code == 200:
                    settings.set('core/latest_version', r.text)

            settings.set('core/last_checked', int(time.time()))

        QNetworkProxyFactory.setUseSystemConfiguration(True)

        #  UI setup etc
        self.menuBars = {
            'file': self.menuBar().addMenu(tr('&File')),
            'annotations': self.menuBar().addMenu(tr('&Annotations')),
            'help': self.menuBar().addMenu(tr('&Help')),
        }


        # GLOBAL WEB SETTINGS
        QNetworkProxyFactory.setUseSystemConfiguration(True)

        # TOOLBAR

        self.setUnifiedTitleAndToolBarOnMac(True) #; // activate Mac-style toolbar


        self.t = QToolBar('File')
        self.t.setIconSize(QSize(22, 22))

        load_configAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'document-open.png')), tr('Load configuration…'), self)
        load_configAction.setStatusTip('Load tool settings and configuration')
        load_configAction.triggered.connect(self.onLoadConfig)
        self.t.addAction(load_configAction)

        save_configAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'document-save.png')), tr('Save configuration…'), self)
        save_configAction.setStatusTip('Save current tool settings and configuration')
        save_configAction.triggered.connect(self.onSaveConfig)
        self.t.addAction(save_configAction)

        self.addToolBar(self.t)

        self.t = QToolBar('Images')
        self.t.setIconSize(QSize(22, 22))

        save_imageAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'image-x-generic.png')), tr('Save current figure…'), self)
        save_imageAction.setStatusTip('Save current spectra figure')
        save_imageAction.triggered.connect(self.onSaveAsImage)
        self.t.addAction(save_imageAction)

        save_all_imageAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'image-x-generic-stack.png')), tr('Save all figures…'), self)
        save_all_imageAction.setStatusTip('Save all spectra figures')
        save_all_imageAction.triggered.connect(self.onSaveAllImage)
        self.t.addAction(save_all_imageAction)

        self.addToolBar(self.t)

        self.t = QToolBar('Spectra')
        self.t.setIconSize(QSize(22, 22))

        hilight_outliersAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'red-square.png')), tr('Highlight outliers'), self)
        hilight_outliersAction.setStatusTip('Highlight outlier spectra in red')
        hilight_outliersAction.setCheckable(True)
        settings.add_handler('spectra/highlight_outliers', hilight_outliersAction)
        hilight_outliersAction.toggled.connect(self.onRefreshCurrentToolPlot)
        self.t.addAction(hilight_outliersAction)

        hilight_classesAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'coloured-squares.png')), tr('Highlight class groups'), self)
        hilight_classesAction.setStatusTip('Highlight spectra by class group (add via Annotations)')
        hilight_classesAction.setCheckable(True)
        settings.add_handler('spectra/highlight_classes', hilight_classesAction)
        hilight_classesAction.toggled.connect(self.onRefreshCurrentToolPlot)
        self.t.addAction(hilight_classesAction)

        annotate_peaksAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'peak.png')), tr('Show peak annotations'), self)
        annotate_peaksAction.setStatusTip('Show peak annotations on spectra')
        annotate_peaksAction.setCheckable(True)
        settings.add_handler('spectra/show_peak_annotations', annotate_peaksAction)
        annotate_peaksAction.toggled.connect(self.onRefreshCurrentToolPlot)
        self.t.addAction(annotate_peaksAction)


        self.addToolBar(self.t)

        self.t = QToolBar('Annotations')
        self.t.setIconSize(QSize(22, 22))

        annotate_classesAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'coloured-squares-picker.png')), tr('Annotate classes'), self)
        annotate_classesAction.setStatusTip('Load class annotations for samples')
        annotate_classesAction.triggered.connect(self.onAnnotateClasses)
        self.t.addAction(annotate_classesAction)

        annotate_peaksAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'peak-picker.png')), tr('Annotate peaks'), self)
        annotate_peaksAction.setStatusTip('Load peak annotations for spectra')
        annotate_peaksAction.triggered.connect(self.onAnnotatePeaks)
        self.t.addAction(annotate_peaksAction)

        self.addToolBar(self.t)

        # INIT PLUGINS AND TOOLS
        # We pass a copy of main window object in to the plugin manager so it can
        # be available for loading

        self.configstack = QStackedWidget()

        self.toolPanel = ui.ToolListWidget(self)
        self.toolPanel.setMinimumWidth(250)
        self.toolPanel.setMaximumWidth(250)

        self.current_tool = None

        self.tools = [
            tools.import_spectra.ImportSpectra(self),

            tools.remove_solvent.RemoveSolvent(self),
            tools.phase_correct.PhaseCorrect(self),


            tools.peak_alignment.PeakAlignment(self),
            tools.baseline_correction.BaselineCorrection(self),
            tools.peak_scaling.PeakScaling(self),

            tools.exclude_regions.ExcludeRegions(self),


            # tools.delete_imaginaries.DeleteImaginaries(self), # Invisible
            # tools.filter.FilterSpectra(self), # Invisible; populated via the spectra panel list (config is there)


            # delete imaginaries


            # realign excluded regions (?) # Correlation shifting remainder regions

            tools.icoshift_.Icoshift(self),

            tools.filter_noise.FilterNoise(self),
            tools.binning.Binning(self),
            tools.compress_bins.CompressBins(self),


            tools.normalisation.Normalisation(self),
            tools.variance_stabilisation.VarianceStabilisation(self),

            tools.pca.PCA(self),

            tools.export_spectra.ExportSpectra(self),

        ]

        for n, tool in enumerate(self.tools):
            item = QListWidgetItem(QIcon(os.path.join(utils.scriptdir, 'icons', tool.icon)), tool.name)
            item.tool = tool
            item.n = n

            tool.item = item

            item.setData(Qt.UserRole, tool)
            item.setData(Qt.UserRole + 1, tool.description)

            item.setData(Qt.UserRole+2, 0.0)  # Progress
            item.setData(Qt.UserRole+3, 'ready') # Status

            self.toolPanel.addItem(item)
            self.configstack.addWidget(tool.configPanels)

            # btn.pressed.connect( lambda t=t: self.configstack.setCurrentWidget(t.configPanels))


        self.toolPanel.currentItemChanged.connect( lambda i: i.tool.activate() )
        self.toolPanel.currentItemChanged.connect( self.update_current_tool_from_item )

        self.main = QWidget()
        self.mainlayout = QHBoxLayout()
        self.centerlayout = QVBoxLayout()
        self.centerlayout.setContentsMargins(0,0,0,0)


        # Set window title and icon

        self.window_title_metadata = {}
        self.setTitle(configuration_filename='Untitled', data_filename='No Data')  # Use default

        # Create status bar
        self.progressBar = QProgressBar(self.statusBar())
        self.progressBar.setMaximumSize(QSize(170, 19))
        self.progressBar.setRange(0, 100)
        self.statusBar().addPermanentWidget(self.progressBar)

        # We need two viewers; one for the scatter plot (PCA) to avoid weird scaling issues
        # when clicking back to spectra
        self.spectraViewer = spectra.SpectraViewer()
        self.pcaViewer = spectra.PCAViewer()

        self.viewStack = QStackedWidget()
        self.viewStack.addWidget(self.spectraViewer)
        self.viewStack.addWidget(self.pcaViewer)
        self.viewStack.setCurrentWidget(self.spectraViewer)



        self.spectraList = ui.SpectraList()
        self.spectraList.setMinimumWidth(250)
        self.spectraList.setMaximumWidth(250)


        self.mainlayout.addWidget( self.toolPanel )

        self.centerlayout.addWidget(self.viewStack)
        self.centerlayout.addWidget( self.configstack )

        self.mainlayout.addLayout( self.centerlayout )

        self.mainlayout.addWidget( self.spectraList )

        self.main.setLayout(self.mainlayout)
        self.setCentralWidget(self.main)

        self.showMaximized()

        self.threadpool = QThreadPool()
        logging.info("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        # Trigger finalise once we're back to the event loop
        self._init_timer1 = QTimer.singleShot(500, self.post_start_test)

    # FIXME: Fugly wrapper to allow set tool on change
    def update_current_tool_from_item(self, item):
        self.current_tool = item.tool

    def onSaveConfig(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save configuration', '', "NMRBrew Config File (*.nmrbrew)")
        if filename:
            '''
            NMRBrew config file is a JSON format storing the tree export from the configuration for individual tools.
            Structure is as follows

            core/<core.config>
            tools/<tool.identifier>/<tool.config>
            '''
            configuration = {
                'version': __version__,
                'created': dt.datetime.now().strftime("%Y-%m-%dT%H:%M%SZ"),
                # Store core configuration for annotations, etc.
                'core': config.as_dict(),
                # Tool configuration
                'tools': {t.__class__.__name__: t.config.as_dict() for t in self.tools }
            }
            with open(filename, 'w') as f:
                json.dump(configuration, f, indent=4)

            self.setTitle(configuration_filename=filename)

    def onLoadConfig(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Load configuration', '', "NMRBrew Config File (*.nmrbrew);;All files (*.*)")
        if filename:

            # Build an access list of all current tools for assignments
            # deactivate any tools not mapped (newer tools added since config saved)
            toolmap = {t.__class__.__name__:t for t in self.tools}

            with open(filename, 'rU') as f:
                configuration = json.load(f)

            config.set_many(configuration['core'])
            for t, c in configuration['tools'].items():
                tool = toolmap[t]
                tool.config.set_many(c)

                print(tool, t, c)

                if tool.config.get('is_active'):
                    tool.enable()
                else:
                    tool.disable()

                del toolmap[t]

            # Deactive any remaining tools
            for t in toolmap.values():
                t.disable()

            self.setTitle(configuration_filename=filename)




    # Init application configuration
    def onResetSettings(self):
        # Reset the QSettings object on the QSettings Manager (will auto-fallback to defined defaults)
        settings.settings.clear()

    def onSaveAsImage(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current figure', '', "Tagged Image File Format (*.tif);;"
                                                                                   "Portable Network Graphics (*.png);;"
                                                                                   "Scalable Vector Graphics (*.svg)")

        if filename:
            exporter = pg.exporters.ImageExporter(self.current_tool.get_plotitem())
            exporter.parameters()['width'] = 2048
            # We need to allow Qt to process or updates/refresh of the plot will not occur
            QApplication.processEvents(QEventLoop.AllEvents)
            exporter.export(filename)

    def onSaveAllImage(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save all figures', '', "Tagged Image File Format (*.tif);;"
                                                                                   "Portable Network Graphics (*.png);;"
                                                                                   "Scalable Vector Graphics (*.svg)")

        if filename:
            # We need to split the filename and add a suffix before the extension for the view name
            basename, ext = os.path.splitext(filename)

            for tool in self.tools:
                if tool.status != 'inactive' and 'spc' in tool.data and tool.data['spc'] is not None:
                    filename = "%s_(%s)%s" % (basename, tool.name, ext)

                    tool.plot(autofit=True)  # Will reset zoom on all plots
                    exporter = pg.exporters.ImageExporter(tool.get_plotitem())
                    exporter.parameters()['width'] = 2048
                    # We need to allow Qt to process or updates/refresh of the plot will not occur
                    QApplication.processEvents(QEventLoop.AllEvents)
                    exporter.export(filename)


    def onAnnotateClasses(self):
        # Present list of sample labels and assigned class (editable ListWidget? Treewidget?)
        # Add/Remove
        # Load from file (CSV, two column)

        # Second list of mapped colours -> class name, QColorButton?
        dlg = ui.AnnotateClasses(self, config=config.as_dict())
        if dlg.exec_():
            # Get result
            config.set('annotation/sample_classes', dlg.config.get('annotation/sample_classes'))
            config.set('annotation/class_colors', dlg.config.get('annotation/class_colors'))

        self.onRefreshCurrentToolPlot()

    def onAnnotatePeaks(self):
        # List of peaks in the spectra to annotate with labels and bars
        # Load from CSV, three column
        # Label, Start, End

        # Second list of mapped colours -> class name, QColorButton?
        dlg = ui.AnnotatePeaks(self, config=config.as_dict())
        if dlg.exec_():
            # Get result
            config.set('annotation/peaks', dlg.config.get('annotation/peaks'))

        self.onRefreshCurrentToolPlot()


    def onRefreshCurrentToolPlot(self, *args, **kwargs):
        self.current_tool.plot()

    def onDoRegister(self):
        # Pop-up a registration window; take an email address and submit to
        # register for update-announce.
        dlg = ui.DialogRegister(self)
        if dlg.exec_():
            # Perform registration
            data = {
                'name': dlg.name.text(),
                'email': dlg.email.text(),
                'country': dlg.country.currentText(),
                'research': dlg.research.text(),
                'institution': dlg.institution.text(),
                'type': dlg.type.currentText(),
                'register': dlg.register.checked(),
            }
            # Send data to server;
            # http://register.pathomx.org POST

    def post_start_test(self):
        return
        # Test data
        import pandas as pd
        data = pd.read_csv('/Users/mxf793/Data/THPNH/Extract/thp1_1d_nmrlab_metabolab.csv', index_col=[0], header=[0,1])
        spc = spectra.Spectra(ppm=data.index.values, data=data.values.T, labels=data.columns.get_level_values(0)) #, classes=data.columns.get_level_values(1))

        self.tools[0].data['spc'] = spc
        self.tools[0].activate()
        self.tools[0].data['spc'].outliers[5] = True

        self.tools[1].data['spc'] = deepcopy(spc)


    def onAbout(self):
        dlg = ui.DialogAbout(self)
        dlg.exec_()

    def onExit(self):
        self.Close(True)  # Close the frame.

    def setTitle(self, configuration_filename=None, data_filename=None):
        if configuration_filename:
            self.window_title_metadata['configuration_filename'] = configuration_filename
        if data_filename:
            self.window_title_metadata['data_filename'] = data_filename

        self.setWindowTitle('%s - NMRBrew - %s' % (
            self.window_title_metadata['configuration_filename'],
            self.window_title_metadata['data_filename'],
        ))


        
def setIcons(app, path, filename):

    if sys.platform == 'win32': # Windows 32/64bit
        import ctypes
        app_identifier = app.organizationDomain() + "." + app.applicationName()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_identifier)
        print(app_identifier)
    icon = QIcon()
    for s in [16,32,64,128]:
        fn = os.path.join(path, filename.format(**{'d': s}))
        print(fn)
        if os.path.exists(fn):
            icon.addFile(fn, QSize(s,s) )
    app.setWindowIcon(icon)

        


def main():

    locale = QLocale.system().name()

    # Load base QT translations from the normal place (does not include _nl, or _it)
    translator_qt = QTranslator()
    if translator_qt.load("qt_%s" % locale, QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        logging.debug(("Loaded Qt translations for locale: %s" % locale))
        app.installTranslator(translator_qt)

    # See if we've got a default copy for _nl, _it or others
    elif translator_qt.load("qt_%s" % locale, os.path.join(utils.scriptdir, 'translations')):
        logging.debug(("Loaded Qt (self) translations for locale: %s" % locale))
        app.installTranslator(translator_qt)

    # Load NMRbrew specific translations
    translator_mp = QTranslator()
    if translator_mp.load("nmrbrew_%s" % locale, os.path.join(utils.scriptdir, 'translations')):
        logging.debug(("Loaded NMRBrew translations for locale: %s" % locale))
    app.installTranslator(translator_mp)

    window = MainWindow()
    
    setIcons(app, os.path.join(utils.scriptdir, 'static'), 'icon_{d}x{d}.png')
    
    logging.info('Ready.')
    app.exec_()  # Enter Qt application main loop


    logging.info('Exiting.')

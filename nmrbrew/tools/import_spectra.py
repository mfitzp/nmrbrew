from .base import ToolBase
from ..ui import ConfigPanel, QFolderLineEdit
from ..globals import settings
from ..qt import *
from .. import utils

class ImportSpectraConfig(ConfigPanel):


    def __init__(self, parent, *args, **kwargs):
        super(ImportSpectraConfig, self).__init__(parent, *args, **kwargs)

        self.v = parent
        gb = QGroupBox('Sample filter')
        gd = QGridLayout()

        pathfreg_le = QLineEdit()
        gd.addWidget(QLabel('Path filter (regexp)'), 1, 0)
        gd.addWidget(pathfreg_le, 1, 1)
        self.config.add_handler('path_filter_regexp', pathfreg_le)

        cb_sampleidfrom = QComboBox()
        cb_sampleidfrom.addItems(['Scan number', 'Experiment (regexp)', 'Path (regexp)'])
        gd.addWidget(QLabel('Sample ID from'), 2, 0)
        gd.addWidget(cb_sampleidfrom, 2, 1)
        self.config.add_handler('sample_id_from', cb_sampleidfrom)

        sample_regexp_le = QLineEdit()
        gd.addWidget(QLabel('Sample ID regexp'), 3, 0)
        gd.addWidget(sample_regexp_le, 3, 1)
        self.config.add_handler('sample_id_regexp', sample_regexp_le)

        cb_classfrom = QComboBox()
        cb_classfrom.addItems(['None', 'Experiment (regexp)', 'Path (regexp)'])
        gd.addWidget(QLabel('Class from'), 4, 0)
        gd.addWidget(cb_classfrom, 4, 1)
        self.config.add_handler('class_from', cb_classfrom)

        class_regexp_le = QLineEdit()
        gd.addWidget(QLabel('Class regexp'), 5, 0)
        gd.addWidget(class_regexp_le, 5, 1)
        self.config.add_handler('class_regexp', class_regexp_le)

        gb.setLayout(gd)
        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)

        gb = QGroupBox('Advanced')
        gd = QGridLayout()

        cb_reverse = QCheckBox()
        gd.addWidget(QLabel('Reverse spectra'), 1, 0)
        gd.addWidget(cb_reverse, 1, 1)
        self.config.add_handler('reverse_spectra', cb_reverse)

        cb_remdf = QCheckBox()
        gd.addWidget(QLabel('Remove digital filter'), 2, 0)
        gd.addWidget(cb_remdf, 2, 1)
        self.config.add_handler('remove_digital_filter', cb_remdf)

        cb_zf = QCheckBox()
        gd.addWidget(QLabel('Zero fill'), 3, 0)
        gd.addWidget(cb_zf, 3, 1)
        self.config.add_handler('zero_fill', cb_zf)

        sp_zf_to = QSpinBox()
        sp_zf_to.setRange(0,65536)
        sp_zf_to.setSingleStep(8192)
        gd.addWidget(sp_zf_to, 4, 1)
        self.config.add_handler('zero_fill_to', sp_zf_to)

        gb.setLayout(gd)

        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)

        self.finalise()


class ImportSpectra(ToolBase):

    name = "Import spectra"
    description = "Load Bruker or Varian format NMR"
    icon = 'bruker.png'

    shortname = 'import'

    is_manual_runnable = False
    is_auto_runnable = False
    is_auto_rerunnable = False
    is_disableable = False

    def __init__(self, *args, **kwargs):
        super(ImportSpectra, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': '',
            'remove_digital_filter': True,
            'reverse_spectra': True,
            'zero_fill': True,
            'zero_fill_to': 32768,

            'path_filter_regexp': '',
            'sample_id_from': 'Scan number',  # Experiment name, Path regexp,
            'sample_id_regexp': '',

            'class_from': 'None',  # Experiment name, Path regexp,
            'class_regexp': '',
        })

        self.addConfigPanel(ImportSpectraConfig)

        load_bruker = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'bruker.png')), 'Import Bruker')
        load_bruker.setToolTip('Load Bruker format NMR spectra')
        load_bruker.pressed.connect(self.onImportBruker)

        self.addButtonBar( [load_bruker] )

    def result(self,*args, **kwargs):
        self.parent().setTitle(data_filename=self.config.get('filename'))
        super(ImportSpectra, self).result(*args, **kwargs)

    def onImportBruker(self):
        """ Open a data file"""
        folder = QFileDialog.getExistingDirectory(self.parent(), 'Open parent folder for your Bruker NMR experiments')
        if folder:
            self.config.set('filename', folder)
            self.run( self.load_bruker )

    @staticmethod
    def load_bruker(spc, config, progress_callback):
        import nmrglue as ng
        import numpy as np
        from ..spectra import Spectra


        def load_bruker_fid(fn, config={}):

            try:
                print("Reading %s" % fn)
                # read in the bruker formatted data
                dic, data = ng.bruker.read(fn) #, read_prog=False)
            except Exception as e:
                print(e)
                return None, None
            else:

                # remove the digital filter
                if config.get('remove_digital_filter'):
                    data = ng.bruker.remove_digital_filter(dic, data)

                # process the spectrum
                original_size = data.shape[-1]

                print(config.get('zero_fill_to'), type(config.get('zero_fill_to')))

                if config.get('zero_fill'):
                    data = ng.proc_base.zf_size(data, config.get('zero_fill_to'))    # zero fill to 32768 points

                #data = ng.process.proc_bl.sol_boxcar(data, w=16, mode='same')  # Solvent removal

                data = ng.proc_base.fft(data)               # Fourier transform

                # data = ng.proc_base.di(data)                # discard the imaginaries

                if config.get('reverse_spectra'):
                    data = ng.proc_base.rev(data)               # reverse the data

                #data = data / 10000000.
                #dic['PATHOMX_PHASE_CORRECT'] = pc
                #dic['PATHOMX_ORIGINAL_SIZE'] = original_size
                return dic, data



        if config['path_filter_regexp']:
            path_filter_regexp = re.compile(config['path_filter_regexp'])
        else:
            path_filter_regexp = None

        if config['sample_id_regexp']:
            sample_id_regexp = re.compile(config['sample_id_regexp'])
        else:
            sample_id_regexp = None

        if config['class_regexp']:
            class_regexp = re.compile(config['class_regexp'])
        else:
            class_regexp = None

        # We should have a folder name; so find all files named fid underneath it (together with path)
        # Extract the path, and the parent folder name (for sample label)
        nmr_data = []
        nmr_dic = []
        sample_labels = []
        sample_classes = []

        _ppm_real_scan_folder = False
        fids = []
        print("Searching for Bruker files in: %s" % config['filename'])
        for r, d, files in os.walk(config['filename']):  # filename contains a folder for Bruker data
            if 'fid' in files:
                scan = os.path.basename(r)
                print('Found Bruker:', r, scan)
                if scan == '99999' or scan == '9999':  # Dummy Bruker thing
                    continue

                if path_filter_regexp:
                    m = path_filter_regexp.search(r)
                    if not m:
                        continue

                # The following is a hack; need some interface for choosing between processed/raw data
                # and for various formats of NMR data input- but simple
                fids.append(r)

        total_fids = len(fids)
        pc_init = None
        pc_history = []
        for n, fid in enumerate(fids):
            print("Loading %d/%d" % (n+1, total_fids))
            dic, data = load_bruker_fid(fid, config)

            if data is not None:

                # Generate sample id for this spectra
                # ['Scan number', 'Experiment name', 'Experiment (regexp)', 'Path (regexp)']
                if config['sample_id_from'] == 'Scan number':
                    label = os.path.basename(fid)

                elif config['sample_id_from'] == 'Sequential':
                    label = str(n + 1)

                elif config['sample_id_from'] == 'Experiment (regexp)':
                    if sample_id_regexp is None:
                        label = dic['acqus']['EXP']

                    else:
                        m = sample_id_regexp.search(dic['acqus']['EXP'])
                        if m:
                            label = m.group(0) if m.lastindex is None else m.group(m.lastindex)

                        else:  # Fallback
                            label = dic['acqus']['EXP']

                elif config['sample_id_from'] == 'Path (regexp)':
                    if sample_id_regexp is None:
                        label = os.path.basename(fid)

                    else:
                        m = sample_id_regexp.search(fid)
                        if m:
                            label = m.group(0) if m.lastindex is None else m.group(m.lastindex)

                        else:  # Fallback
                            label = fid

                else:
                    label = os.path.basename(fid)


                # Generate sample id for this spectra
                # ['Scan number', 'Experiment name', 'Experiment (regexp)', 'Path (regexp)']
                if config['class_from'] == 'None':
                    classn = ''

                elif config['class_from'] == 'Experiment (regexp)':
                    if class_regexp is None:
                        classn = dic['acqus']['EXP']

                    else:
                        m = class_regexp.search(dic['acqus']['EXP'])
                        if m:
                            classn = m.group(0) if m.lastindex is None else m.group(m.lastindex)

                        else:  # Fallback
                            classn = dic['acqus']['EXP']

                elif config['class_from'] == 'Path (regexp)':
                    if class_regexp is None:
                        classn = os.path.basename(fid)

                    else:
                        m = class_regexp.search(fid)
                        if m:
                            classn = m.group(0) if m.lastindex is None else m.group(m.lastindex)

                        else:  # Fallback
                            classn = fid

                else:
                    classn = ''
                #if 'AUTOPOS' in dic['acqus']:
                #    label = label + " %s" % dic['acqus']['AUTOPOS']

                sample_labels.append(label)
                sample_classes.append(classn)

                nmr_data.append(data)
                nmr_dic.append(dic)
                _ppm_real_scan_folder = fid

            progress_callback(float(n) / total_fids)  # Emit progress update

        if _ppm_real_scan_folder:
            # Nothing worked

            # Generate the ppm for these spectra
            # read in the bruker formatted data// use latest
            dic, data_unp = ng.bruker.read(_ppm_real_scan_folder) #
            # Calculate ppms
            # SW total ppm 11.9877
            # SW_h total Hz 7194.244
            # SF01 Hz of 0ppm 600
            # TD number of data points 32768

            # Offset (not provided but we have:
            # O1 Hz offset (shift) of spectra 2822.5 centre!
            # BF ? 600Mhz
            # O1/BF = centre of the spectra
            # OFFSET = (SW/2) - (O1/BF)

            # What we need to calculate is start, end, increment
            offset = (float(dic['acqus']['SW']) / 2) - (float(dic['acqus']['O1']) / float(dic['acqus']['BF1']))
            start = float(dic['acqus']['SW']) - offset
            end = -offset
            step = float(dic['acqus']['SW']) / 32768

            nmr_ppms = np.arange(start, end, -step)[:32768]


            spectra = Spectra(data=np.array(nmr_data), ppm=nmr_ppms, labels=sample_labels, classes=sample_classes)

            spectra.metadata = {
                'experiment_name': '%s (%s)' % (dic['acqus']['EXP'], config['filename']),

            }

            return {'spc': spectra }


        else:
            raise Exception("No valid data found")

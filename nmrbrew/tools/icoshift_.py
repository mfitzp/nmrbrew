from .base import ToolBase
from ..ui import ConfigPanel, QFolderLineEdit, QNoneDoubleSpinBox
from ..globals import settings
from ..qt import *

from collections import defaultdict

class IcoshiftConfig(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(IcoshiftConfig, self).__init__(*args, **kwargs)

        self.display_options = defaultdict(dict)
        self.config.updated.connect(self.change_display)

        gb = QGroupBox('Basic')
        gd = QGridLayout()
        gb.setLayout(gd)
        self.target_cb = QComboBox()
        self.target_cb.addItems(['average', 'median', 'max', 'average2', 'spectra_number'])
        self.config.add_handler('target', self.target_cb)
        gd.addWidget(self.target_cb, 0, 0)

        average2_sb = QSpinBox()
        self.config.add_handler('average2_multiplier', average2_sb)
        self.display_options['target']['average2'] = (average2_sb,)

        spectran_sb = QSpinBox()
        spectran_sb.setMinimum(0)
        self.config.add_handler('spectra_number', spectran_sb)
        self.display_options['target']['spectra_number'] = (spectran_sb,)

        l = QHBoxLayout()
        l.addWidget(average2_sb)
        l.addWidget(spectran_sb)
        gd.addLayout(l, 0, 1)

        self.mode_cb = QComboBox()
        self.mode_cb.addItems(['whole', 'number_of_intervals', 'length_of_intervals', 'selected_intervals'])  # , 'define', 'reference_signal'])
        self.config.add_handler('intervals', self.mode_cb)
        gd.addWidget(self.mode_cb, 2, 0)

        number_int_sb = QSpinBox()

        self.config.add_handler('number_of_intervals', number_int_sb)
        self.display_options['intervals']['number_of_intervals'] = (number_int_sb, )

        length_intervals_sb = QSpinBox()
        self.config.add_handler('length_of_intervals', length_intervals_sb)
        self.display_options['intervals']['length_of_intervals'] = (length_intervals_sb,)

        l = QHBoxLayout()
        l.addWidget(number_int_sb)
        l.addWidget(length_intervals_sb)
        gd.addLayout(l, 2, 1)


        self.mode_cb = QComboBox()
        self.mode_cb.addItems(['n', 'b', 'f'])
        self.config.add_handler('maximum_shift', self.mode_cb)
        gd.addWidget(self.mode_cb, 3, 0)

        maxshift_sb = QSpinBox()
        self.config.add_handler('maximum_shift_n', maxshift_sb)
        gd.addWidget(maxshift_sb, 3, 1)
        self.display_options['maximum_shift']['n'] = (maxshift_sb,)

        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)

        gb = QGroupBox('Co-shift preprocessing')
        gd = QGridLayout()
        gb.setLayout(gd)

        self.coshift_btn = QCheckBox('Enable co-shift preprocessing')
        #self.coshift_btn.setCheckable( True )
        self.config.add_handler('coshift_preprocessing', self.coshift_btn)
        gd.addWidget(self.coshift_btn, 0, 0)

        self.coshift_max_cb = QNoneDoubleSpinBox()
        self.config.add_handler('coshift_preprocessing_max_shift', self.coshift_max_cb)
        gd.addWidget(QLabel('Maximum shift'), 1, 0)
        gd.addWidget(self.coshift_max_cb, 1, 1)

        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)

        gb = QGroupBox('Miscellaneous')
        gd = QGridLayout()
        gb.setLayout(gd)

        self.fill_previous = QCheckBox('Fill shifted regions with previous value')
        #self.coshift_btn.setCheckable( True )
        self.config.add_handler('fill_with_previous', self.fill_previous)
        gd.addWidget(self.fill_previous, 0, 0)

        self.addBottomSpacer(gd)
        self.layout.addWidget(gb)


        self.change_display()  # Set starting state
        self.finalise()

    def change_display(self, *args):
        for k, v in self.display_options.items():
            ic = self.config.get(k)
            for i, o in v.items():
                for oo in o:
                    if i == ic:
                        oo.show()
                    else:
                        oo.hide()


class Icoshift(ToolBase):

    name = "Icoshift"
    description = "Correlation shift spectra"
    shortname = 'ic'
    icon = 'icoshift.png'

    def __init__(self, *args, **kwargs):
        super(Icoshift, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'target': 'average',
            'intervals': 'whole',
            'maximum_shift': 'f',
            'maximum_shift_n': 50,
            'coshift_preprocessing': False,
            'coshift_preprocessing_max_shift': None,
            'average2_multiplier': 3,
            'number_of_intervals': 50,
            'fill_with_previous': True,
            'spectra_number': 0,

            'selected_data_regions': [],
        })

        self.addConfigPanel(IcoshiftConfig)
        self.addButtonBar(self.deftaultButtons())

    def run_manual(self):
        self.run( self.shift )


    @staticmethod
    def shift(spc, config, progress_callback):
        from icoshift import icoshift
        import pandas as pd
        import numpy as np

        # Remove imaginaries
        spc.data = np.real(spc.data)

        if config['intervals'] == 'whole':
            intervals = 'whole'

        elif config['intervals'] == 'number_of_intervals':
            intervals = config['number_of_intervals']

        elif config['intervals'] == 'length_of_intervals':
            intervals = config['length_of_intervals']

        elif config['intervals'] == 'selected_intervals':
            regions = config['selected_data_regions']
            if regions is None or regions == []:
                intervals = 'whole'
            else:
                intervals = []

                def find_index_of_nearest(l, v):
                    return min(range(len(l)), key=lambda i: abs(l[i] - v))

                scal

                for r in regions:
                    if r[0] == 'View':
                        x0, y0, x1, y1 = r[1:]
                        # Convert from data points to indexes
                        intervals.append((find_index_of_nearest(spc.ppm, x0), find_index_of_nearest(spc.ppm, x1)))

        if config['maximum_shift'] == 'n':
            maximum_shift = config['maximum_shift_n']
        else:
            maximum_shift = config['maximum_shift']


        if config['target'] == 'spectra_number':
            target = spc[config['spectra_number'], :].reshape(1, -1)

        else:
            target = config['target']

        xCS, ints, ind, target = icoshift(target, spc.data,
                                          inter=intervals,
                                          n=maximum_shift,
                                          coshift_preprocessing=config['coshift_preprocessing'],
                                          coshift_preprocessing_max_shift=config['coshift_preprocessing_max_shift'],
                                          average2_multiplier=config['average2_multiplier'],
                                          fill_with_previous=config['fill_with_previous'],
                                                                       )

        spc.data = xCS

        return {'spc': spc}

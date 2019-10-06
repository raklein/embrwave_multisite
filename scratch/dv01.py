import csv
import os
import random
import logging

import PyQt5.QtWidgets as qtw
from pip._vendor import pytoml as toml
from PyQt5.QtCore import Qt
from my_widgets import MultiQuestion


class BaseDV(qtw.QWidget):
    _log = logging.getLogger('embr_survey')

    def __init__(self, block_num, temperature, settings):
        super().__init__()
        self.settings = settings
        self.block_num = block_num
        self.temperature = temperature

    def save_data(self):
        pass


class SimpleDV(BaseDV):

    def __init__(self, block_num, temperature, settings):
        super().__init__(block_num, temperature, settings)
        lang = settings['language']
        translation_path = os.path.join(settings['translation_dir'], '%s.toml' % self.short_name)
        with open(translation_path, 'r') as f:
            translation = toml.load(f)

        prompt = translation['prompt'][lang]
        header = translation['header'][lang]
        self.questions = [('q%i' % i, q[lang]) for i, q in enumerate(translation['question'])]
        random.shuffle(self.questions)

        layout = qtw.QVBoxLayout()
        self.qs = MultiQuestion(header, [q[1] for q in self.questions])
        head = qtw.QLabel(prompt)
        head.setStyleSheet('font-size:26pt;')
        head.setWordWrap(True)
        layout.addWidget(head)
        layout.addWidget(self.qs)
        self.setLayout(layout)

    def save_data(self):
        current_answers = self.qs.get_responses()
        settings = self.settings
        now = self._start_time.strftime('%y%m%d_%H%M%S')
        csv_name = os.path.join(settings['data_dir'], '%s_%s.csv' % (self.short_name, now))
        num_q = len(self.questions)
        data = {'participant_id': num_q * [settings['id']],
                'datetime_start_exp': num_q * [settings['datetime_start']],
                'datetime_start_block': num_q * [now],
                'datetime_end_block': num_q * [self._end_time.strftime('%y%m%d_%H%M%S')],
                'language': num_q * [settings['language']],
                'locale': num_q * [settings['locale']],
                'questions': [q[1][:30] + '...' for q in self.questions],
                'question_original_order': [q[0] for q in self.questions],
                'responses': current_answers,
                'dv': num_q * [self.name],
                'block_number': num_q * [self.block_num],
                'embr_temperature': num_q * [self.temperature]}
        keys = sorted(data.keys())
        with open(csv_name, "w") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(keys)
            writer.writerows(zip(*[data[key] for key in keys]))


class DV01SimilarityObjects(SimpleDV):
    name = 'dv01_similarity_objects'
    short_name = 'dv01'


if __name__ == '__main__':
    from datetime import datetime
    from base_area import MainWindow

    app = qtw.QApplication([])

    holder = qtw.QLabel('Start.')
    now = datetime.now().strftime('%y%m%d_%H%M%S')
    dv1 = DV01SimilarityObjects(1, 9,  {'language': 'en', 'translation_dir': './',
                                        'data_dir': './data/', 'id': 'test',
                                        'datetime_start': now, 'locale': 'us'})

    stack = [holder, dv1]
    window = MainWindow(stack)
    app.exec_()

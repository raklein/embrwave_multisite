import sys
from time import sleep
from PySide2.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
import PySide2.QtWidgets as qtw
from functools import partial
from datetime import datetime
from embr_survey.common_widgets import SpecialStack

base_style = '''
QPushButton {border:4px solid rgb(0, 0, 0); 
             border-radius:10px;
             font: bold 40px;padding: 24px;}
QPushButton:pressed {border-style:inset;}
'''

incomplete_style = '''
QPushButton {background-color: rgb(255, 140, 0);}
QPushButton:pressed {background-color: rgb(255, 165, 0);}
'''

resp_style = '''
QPushButton {background-color: rgb(0,255,127);}
QPushButton:pressed {background-color: rgb(0,230,134);}
'''

no_style = '''
QPushButton {background-color: rgb(120, 120, 120);color:rgb(40,40,40);}
'''


class NextButton(qtw.QPushButton):
    def __init__(self, height, stack, win):
        super().__init__('Next')
        self.setFixedHeight(0.1*height)
        self.setStyleSheet(base_style)
        self.stack = stack
        self.clicked.connect(self._callback)
        self.state = 'complete'
        self.incomplete_txt = 'Are you sure? You left some blank.'
        self.win = win

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        if value == 'neutral':
            new_sty = no_style
            self.setDisabled(True)
        elif value == 'incomplete':
            new_sty = incomplete_style
            self.setEnabled(True)
        elif value == 'complete':
            new_sty = resp_style
            self.setEnabled(True)
        self.setStyleSheet(base_style + new_sty)

    def _callback(self):
        # divided into three parts for potential animations between
        # sections-- however, the attempt (9496818f6a9b7ae3694a7f77faa354d96351a53a)
        # seemed to lead to "smearing" artifacts on subsequent widgets...
        current = self.stack.currentWidget()
        try:
            all_ans = current.all_ans()
        except AttributeError:  # no all_ans attribute, probably a regular widget
            all_ans = True
        if self.state == 'neutral':
            return
        if self.state == 'incomplete' or not all_ans:
            choice = qtw.QMessageBox.question(None, '',
                                              self.incomplete_txt,
                                              qtw.QMessageBox.Yes | qtw.QMessageBox.No)
            if choice != qtw.QMessageBox.Yes:
                return
        # all good to keep going, save data (no-op for instructions, but important for surveys)
        self._animate(current, 300, 1, 0, self._callback_pt2)
        #self._callback_pt2()

    # part 2
    # need to:
    # - pop off previous widget
    # - if we're out of widgets, exit
    def _callback_pt2(self):
        current_widget = self.stack.currentWidget()
        # handle when the current widget is a Stack
        if isinstance(current_widget, SpecialStack):
            # consume a subwidget
            c2 = current_widget.currentWidget()
            c2.setSizePolicy(qtw.QSizePolicy.Ignored, qtw.QSizePolicy.Ignored)
            # current_widget.adjustSize()
            if hasattr(c2, 'on_exit'):
                c2.on_exit()
            # move to the next subwidget
            current_widget.removeWidget(c2)
            if current_widget.count() > 0:
                # resize to subwidget
                c3 = current_widget.currentWidget()
                c3.setSizePolicy(qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Expanding)
                c3.adjustSize()
                current_widget.adjustSize()
                self.stack.adjustSize()
                if hasattr(c3, 'on_enter'):
                    c3.on_enter()
                if getattr(c3, 'auto_continue', True):
                    cb = self._callback_pt3
                #QTimer.singleShot(1000, self._callback_pt3)
                else:
                    cb = self._dummy
                self._animate(c3, 700, 0, 1, cb)

        # if we're ready to go to the next widget
        if not isinstance(current_widget, SpecialStack) or current_widget.count() <= 0:
            current_widget._end_time = datetime.now()
            if hasattr(current_widget, 'on_exit'):
                current_widget.on_exit()  # call additional cleanup things
            # implement a save_data if doing a survey section
            if hasattr(current_widget, 'save_data'):
                current_widget.save_data()
            self.state = 'neutral'
            passed_data = getattr(current_widget, 'passed_data', None)
            current_widget.setSizePolicy(qtw.QSizePolicy.Ignored,
                                         qtw.QSizePolicy.Ignored)
            self.stack.adjustSize()
            self.stack.removeWidget(current_widget)
            if self.stack.count() <= 0:
                sys.exit(0)
            # move to the next one
            new_widget = self.stack.currentWidget()
            if passed_data is not None:
                new_widget.passed_data = passed_data
            if hasattr(new_widget, 'on_enter'):
                new_widget.on_enter()  # call one-shot things (generally for controlling temperature)
            new_widget._start_time = datetime.now()
            new_widget.setSizePolicy(qtw.QSizePolicy.Expanding,
                                     qtw.QSizePolicy.Expanding)
            new_widget.adjustSize()
            self.stack.adjustSize()

            if getattr(new_widget, 'auto_continue', True):
                cb = self._callback_pt3
                #QTimer.singleShot(1000, self._callback_pt3)
            else:
                cb = self._dummy
            self._animate(new_widget, 700, 0, 1, cb)

    def _dummy(self):
        pass

    def _callback_pt3(self):
        # re-enable the button on completion
        self.state = 'complete'

    def _animate(self, current, duration, start, end, callback):
        if end == 1:
            self.win.scroll_up()
        self.eff = qtw.QGraphicsOpacityEffect()
        current.setGraphicsEffect(self.eff)
        a = QPropertyAnimation(self.eff, b'opacity')
        a.setDuration(duration)
        a.setStartValue(start)
        a.setEndValue(end)
        a.setEasingCurve(QEasingCurve.Linear)
        a.finished.connect(callback)
        a.start(QPropertyAnimation.DeleteWhenStopped)
        self.a = a

import pandas as pd
from PyQt5.QtWidgets import QFileDialog

class FileBrowser:
    def __init__(self, parent):
        self.parent = parent

    def browse_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        fileName, _ = QFileDialog.getOpenFileName(self.parent,"QFileDialog.getOpenFileName()", "","All Files (*);;CSV Files (*.csv);;DAT Files (*.dat);;XLSX Files (*.xlsx);;TXT Files (*.txt)", options=options)
        if fileName:
            return self.read_file(fileName)
        else:
            return None, None

    def read_file(self, fileName):
        if fileName.endswith('.csv'):
            df = pd.read_csv(fileName)
        elif fileName.endswith('.xlsx'):
            df = pd.read_excel(fileName)
        elif fileName.endswith('.dat') or fileName.endswith('.txt'):
            df = pd.read_csv(fileName, sep='\t')
        time = df['Time'].values
        amplitude = df['Amplitude'].values
        return time, amplitude



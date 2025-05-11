if __name__ == "__main__":
    from lmpnn_gui_pymol import check_installation_windows
    from PyQt5.QtWidgets import QApplication, QWidget
    import sys

    qt = QApplication(sys.argv)
    main = QWidget()
    main.show()
    check_installation_windows()

    sys.exit(qt.exec_())
    

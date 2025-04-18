import sys
from PyQt5.QtWidgets import QApplication
from ui import UIComponents

def main():
    app = QApplication(sys.argv)
    player = UIComponents()
    player.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

from database import CaseDB
from graphical import TesisApp

if __name__ == "__main__":
    db = CaseDB(dbname="tesis", user="postgres", password="My_password", host="localhost")
    db.connect()

    app = TesisApp(db)
    app.mainloop()

    db.close()

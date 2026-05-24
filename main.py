from database import CaseDB
from graphical import TesisApp

if __name__ == "__main__":
    db = CaseDB(dbname="tesis", user="postgres", password="perro", host="localhost")
    db.connect()

    app = TesisApp(db)
    app.mainloop()

    db.close()

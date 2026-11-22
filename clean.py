import sqlite3
c = sqlite3.connect("instance/examination-portal6.sqlite3")
c.execute("DELETE FROM slot")
c.commit()
print("done")
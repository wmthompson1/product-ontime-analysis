import sqlite3
connection = sqlite3.connect("database1.db")
c = connection.cursor()

c.execute("CREATE TABLE IF NOT EXISTS table1(hats, shirts, pants, shoes, glasses)")
c.execute("INSERT INTO table1 VALUES('Baseball', 'Henley', 'Khakis', 'Sneakers', 'Sunglasses')")
connection.commit()

# How to insert data with variable formatting
#c.execute("INSERT INTO table1 (hats, shirts, pants, shoes, glasses) VALUES(?, ?, ?, ?, ?)", (var1, var2, var3, var4, var5))

c.execute('SELECT * FROM table1')
fetched_data = c.fetchall()
print(fetched_data)

# How to customize searches
#c.execute("SELECT * FROM table1 WHERE value=’TargetValue’ AND keyword=’TargetKeyword’ ")
#fetched_data = c.fetchall()

# How to update and delete values
#c.execute("UPDATE table1 SET value = 'NewValue' WHERE value = 'OldValue'")
#c.execute("DELETE FROM table1 WHERE value = ‘ValueToDelete’")

c.close()
connection.close()

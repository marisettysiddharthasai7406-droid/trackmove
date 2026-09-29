import sqlite3

connection = sqlite3.connect("database.db")
cursor = connection.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("TABLES:")
for table in tables:
    print(table[0])

print("\nBUSES:")
cursor.execute("SELECT * FROM buses")

for bus in cursor.fetchall():
    print(bus)

connection.close()
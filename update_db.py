import sqlite3

connection = sqlite3.connect("database.db")

cursor = connection.cursor()

cursor.execute("PRAGMA table_info(buses)")

columns = [row[1] for row in cursor.fetchall()]

if "current_stop" not in columns:

    cursor.execute("""
        ALTER TABLE buses
        ADD COLUMN current_stop INTEGER DEFAULT 1
    """)

    print("Added current_stop column.")

else:

    print("current_stop already exists.")


if "progress" not in columns:

    cursor.execute("""
        ALTER TABLE buses
        ADD COLUMN progress REAL DEFAULT 0
    """)

    print("Added progress column.")

else:

    print("progress already exists.")


cursor.execute("""
    UPDATE buses
    SET current_stop = 1
    WHERE current_stop IS NULL
""")


cursor.execute("""
    UPDATE buses
    SET progress = 0
    WHERE progress IS NULL
""")


connection.commit()


print()
print("DATABASE UPDATED SUCCESSFULLY")
print()


cursor.execute("PRAGMA table_info(buses)")

print("BUSES TABLE COLUMNS:")

for column in cursor.fetchall():

    print(column)


connection.close()
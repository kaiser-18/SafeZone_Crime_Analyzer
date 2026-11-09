import sqlite3

conn = sqlite3.connect("safezone.db")
cursor = conn.cursor()

cursor.execute("""
    DELETE FROM crimes
    WHERE area IN (
        'Zone A',
        'Zone B',
        'Zone C',
        'Zone D',
        'Zone E'
    )
""")

print("Deleted records:", cursor.rowcount)

conn.commit()
conn.close()

print("Zone records deleted successfully!")
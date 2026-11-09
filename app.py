

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "safezone.db")



def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crime_type TEXT,
            area TEXT,
            year INTEGER,
            cases INTEGER,
            latitude REAL,
            longitude REAL
        )
    """)

    cursor.execute("PRAGMA table_info(crimes)")
    columns = [column[1] for column in cursor.fetchall()]

    if "latitude" not in columns:
        cursor.execute("ALTER TABLE crimes ADD COLUMN latitude REAL")

    if "longitude" not in columns:
        cursor.execute("ALTER TABLE crimes ADD COLUMN longitude REAL")

    cursor.execute("SELECT COUNT(*) FROM crimes")

    if cursor.fetchone()[0] == 0:
        sample_data = [
            ("Theft", "Zone A", 2024, 20),
            ("Assault", "Zone B", 2024, 10),
            ("Fraud", "Zone C", 2025, 15),
            ("Vandalism", "Zone A", 2025, 8),
            ("Theft", "Zone D", 2025, 25)
        ]

        cursor.executemany("""
            INSERT INTO crimes (crime_type, area, year, cases)
            VALUES (?, ?, ?, ?)
        """, sample_data)

    conn.commit()
    conn.close()



@app.route("/")
def home():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Overall dashboard statistics
    cursor.execute("SELECT SUM(cases) FROM crimes")
    total_cases = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(DISTINCT crime_type) FROM crimes")
    categories = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT area) FROM crimes")
    areas = cursor.fetchone()[0]

    # Read selected filters
    selected_crime = request.args.get("crime_type", "All")
    selected_year = request.args.get("year", "All")
    selected_area = request.args.get("area", "All")

    # Build a safe database filter
    conditions = []
    values = []

    if selected_crime != "All":
        conditions.append("crime_type = ?")
        values.append(selected_crime)

    if selected_year != "All":
        conditions.append("year = ?")
        values.append(selected_year)

    if selected_area != "All":
        conditions.append("area = ?")
        values.append(selected_area)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Filtered crime records
    cursor.execute(f"""
        SELECT crime_type, area, year, cases
        FROM crimes
        {where_clause}
        ORDER BY year DESC, id DESC
    """, values)
    records = cursor.fetchall()

    # Total cases matching filters
    cursor.execute(f"""
        SELECT SUM(cases)
        FROM crimes
        {where_clause}
    """, values)
    filtered_total = cursor.fetchone()[0] or 0

    # Dropdown options
    cursor.execute("SELECT DISTINCT crime_type FROM crimes ORDER BY crime_type")
    crime_types = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT year FROM crimes ORDER BY year")
    years = [str(row[0]) for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT area FROM crimes ORDER BY area")
    area_names = [row[0] for row in cursor.fetchall()]

    # Crime category analytics
    cursor.execute("""
        SELECT crime_type, SUM(cases)
        FROM crimes
        GROUP BY crime_type
    """)
    category_data = cursor.fetchall()

    # Yearly crime analytics
    cursor.execute("""
        SELECT year, SUM(cases)
        FROM crimes
        GROUP BY year
        ORDER BY year
    """)
    year_data = cursor.fetchall()

    # Area-wise crime data for map
    cursor.execute("""
        SELECT area, SUM(cases)
        FROM crimes
        GROUP BY area
    """)
    area_data = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_cases=total_cases,
        categories=categories,
        areas=areas,
        records=records,
        filtered_total=filtered_total,
        crime_types=crime_types,
        years=years,
        area_names=area_names,
        selected_crime=selected_crime,
        selected_year=selected_year,
        selected_area=selected_area,
        message=request.args.get("message"),
        category_data=category_data,
        year_data=year_data,
        area_data=area_data
    )



@app.route("/map")
def map_page():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT area, SUM(cases), latitude, longitude
        FROM crimes
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
        GROUP BY area, latitude, longitude
    """)
    area_data = cursor.fetchall()

    cursor.execute("""
        SELECT area, crime_type, SUM(cases)
        FROM crimes
        GROUP BY area, crime_type
        ORDER BY area, crime_type
    """)
    category_data = cursor.fetchall()

    conn.close()

    return render_template(
        "map.html",
        area_data=area_data,
        category_data=category_data
    )





@app.route("/analytics")
def analytics_page():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Crime by category
    cursor.execute("""
        SELECT crime_type, SUM(cases)
        FROM crimes
        GROUP BY crime_type
    """)
    category_data = cursor.fetchall()

    # Yearly crime trends
    cursor.execute("""
        SELECT year, SUM(cases)
        FROM crimes
        GROUP BY year
        ORDER BY year
    """)
    year_data = cursor.fetchall()

    # Available areas
    cursor.execute("""
        SELECT DISTINCT area
        FROM crimes
        ORDER BY area
    """)
    areas = [row[0] for row in cursor.fetchall()]

    # Available years
    cursor.execute("""
        SELECT DISTINCT year
        FROM crimes
        ORDER BY year
    """)
    years = [row[0] for row in cursor.fetchall()]

    # Detailed area and year information
    cursor.execute("""
        SELECT year, area, crime_type, SUM(cases)
        FROM crimes
        GROUP BY year, area, crime_type
        ORDER BY year, area, crime_type
    """)
    detail_data = cursor.fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        category_data=category_data,
        year_data=year_data,
        areas=areas,
        years=years,
        detail_data=detail_data
    )




@app.route("/search")
def search_page():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    selected_crime = request.args.get("crime_type", "All")
    selected_year = request.args.get("year", "All")
    selected_area = request.args.get("area", "All")
    search_text = request.args.get("q", "").strip()

    conditions = []
    values = []

    if selected_crime != "All":
        conditions.append("crime_type = ?")
        values.append(selected_crime)

    if selected_year != "All":
        conditions.append("year = ?")
        values.append(selected_year)

    if selected_area != "All":
        conditions.append("area = ?")
        values.append(selected_area)

    if search_text:
        conditions.append("""
            (
                crime_type LIKE ?
                OR area LIKE ?
                OR CAST(year AS TEXT) LIKE ?
                OR CAST(cases AS TEXT) LIKE ?
            )
        """)
        search_value = f"%{search_text}%"
        values.extend([search_value] * 4)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Get filtered records
    cursor.execute(f"""
        SELECT id, crime_type, area, year, cases
        FROM crimes
        {where_clause}
        ORDER BY year DESC
    """, values)
    records = cursor.fetchall()

    total_records = len(records)
    total_cases = sum(row[4] for row in records)
    total_locations = len(set(row[2] for row in records))
    # Get statistics for filtered records
    cursor.execute(f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(cases), 0),
            COUNT(DISTINCT area),
            COUNT(DISTINCT crime_type)
        FROM crimes
        {where_clause}
    """, values)

    stats = cursor.fetchone()

    # Dropdown options
    cursor.execute("""
        SELECT DISTINCT crime_type
        FROM crimes
        ORDER BY crime_type
    """)
    crime_types = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT year
        FROM crimes
        ORDER BY year
    """)
    years = [str(row[0]) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT area
        FROM crimes
        ORDER BY area
    """)
    area_names = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "search.html",
        total_records=total_records,
        total_cases=total_cases,
        total_locations=total_locations,
        records=records,
        crime_types=crime_types,
        years=years,
        area_names=area_names,
        selected_crime=selected_crime,
        selected_year=selected_year,
        selected_area=selected_area,
        search_text=search_text,
        stats=stats
    )



@app.route("/records")
def records_page():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, crime_type, area, year, cases
        FROM crimes
        ORDER BY year DESC, id DESC
    """)

    records = cursor.fetchall()
    conn.close()

    return render_template(
        "records.html",
        records=records,
        message=request.args.get("message")
    )
@app.route("/delete-crime/<int:record_id>", methods=["POST"])
def delete_crime(record_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM crimes WHERE id = ?",
        (record_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for(
        "records_page",
        message="Crime record deleted successfully!"
    ))


@app.route("/edit-crime/<int:record_id>", methods=["GET", "POST"])
def edit_crime(record_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":

        crime_type = request.form.get("crime_type", "").strip()
        area = request.form.get("area", "").strip()

        try:
            year = int(request.form.get("year"))
            cases = int(request.form.get("cases"))

            if not crime_type or not area or cases < 1 or year < 1900 or year > 2100:
                raise ValueError

        except (ValueError, TypeError):
            conn.close()
            return redirect(url_for(
                "records_page",
                message="Invalid record details!"
            ))

        cursor.execute("""
            UPDATE crimes
            SET crime_type = ?, area = ?, year = ?, cases = ?
            WHERE id = ?
        """, (crime_type, area, year, cases, record_id))

        conn.commit()
        conn.close()

        return redirect(url_for(
            "records_page",
            message="Crime record updated successfully!"
        ))

    cursor.execute("""
        SELECT id, crime_type, area, year, cases
        FROM crimes
        WHERE id = ?
    """, (record_id,))

    record = cursor.fetchone()
    conn.close()

    if record is None:
        return redirect(url_for(
            "records_page",
            message="Record not found!"
        ))

    return render_template("edit_record.html", record=record)


@app.route("/add-crime", methods=["POST"])
def add_crime():

    crime_type = request.form.get("crime_type", "").strip()
    area = request.form.get("area", "").strip()

    try:
        year = int(request.form.get("year", ""))
        cases = int(request.form.get("cases", ""))

        if not crime_type or not area:
            raise ValueError

        if not 1900 <= year <= 2100 or cases < 1:
            raise ValueError

    except ValueError:
        return redirect(url_for(
            "home", message="Invalid input. Please check your details."
        ))

    # Find the location in India
    latitude = None
    longitude = None

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": area + ", India",
                "format": "json",
                "limit": 1
            },
            headers={"User-Agent": "SafeZoneCrimeAnalyzer/1.0"},
            timeout=10
        )

        response.raise_for_status()
        results = response.json()

        if results:
            latitude = float(results[0]["lat"])
            longitude = float(results[0]["lon"])

    except requests.RequestException:
        pass

    if latitude is None:
        return redirect(url_for(
            "records_page",
            message="Location not found. Enter a more specific place name."
        ))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO crimes
        (crime_type, area, year, cases, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (crime_type, area, year, cases, latitude, longitude))

    conn.commit()
    conn.close()

    return redirect(url_for(
        "records_page", message="Crime record added successfully!"
    ))
if __name__ == "__main__":
    init_db()
    app.run(debug=True)


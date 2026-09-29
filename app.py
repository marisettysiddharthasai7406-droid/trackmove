from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import time
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# ADMIN CREDENTIALS
# =========================================================

ADMIN_USERNAME = "admin"

ADMIN_PASSWORD_HASH = generate_password_hash(
    "TrackMove@Admin123"
)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "trackmove_secret_key"

DATABASE = "database.db"


# =========================================================
# SIMULATION SETTINGS
# =========================================================

SEGMENT_TIME = 300


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    # Enable foreign keys
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# =========================================================
# CREATE / MIGRATE DATABASE
# =========================================================

def create_database():

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # ROUTES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_number TEXT UNIQUE NOT NULL,
            route_name TEXT NOT NULL,
            start_location TEXT NOT NULL,
            destination TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # STOPS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            stop_order INTEGER NOT NULL,
            stop_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            FOREIGN KEY (route_id)
                REFERENCES routes(id)
                ON DELETE CASCADE
        )
    """)

    # -----------------------------------------------------
    # BUSES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT UNIQUE NOT NULL,
            driver_name TEXT,
            route_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Available',
            latitude REAL,
            longitude REAL,
            current_stop INTEGER DEFAULT 1,
            progress REAL DEFAULT 0,
            started_at REAL,
            trip_direction TEXT DEFAULT 'OUTBOUND',
            trip_started INTEGER DEFAULT 0,
            FOREIGN KEY (route_id)
                REFERENCES routes(id)
        )
    """)

    # -----------------------------------------------------
    # MIGRATE OLD DATABASE
    # -----------------------------------------------------

    cursor.execute("PRAGMA table_info(buses)")

    columns = [
        column["name"]
        for column in cursor.fetchall()
    ]

    if "started_at" not in columns:

        cursor.execute("""
            ALTER TABLE buses
            ADD COLUMN started_at REAL
        """)

    if "trip_direction" not in columns:

        cursor.execute("""
            ALTER TABLE buses
            ADD COLUMN trip_direction TEXT DEFAULT 'OUTBOUND'
        """)

    if "trip_started" not in columns:

        cursor.execute("""
            ALTER TABLE buses
            ADD COLUMN trip_started INTEGER DEFAULT 0
        """)

    cursor.execute("""
        UPDATE buses
        SET status = 'Available'
        WHERE status = 'Inactive'
    """)

    # -----------------------------------------------------
    # DEFAULT DEMO DATA
    #
    # Only create the demo route if there are no routes.
    # This prevents a deleted route from coming back.
    # -----------------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM routes
    """)

    route_count = cursor.fetchone()["count"]

    if route_count == 0:

        cursor.execute("""
            INSERT INTO routes
            (
                route_number,
                route_name,
                start_location,
                destination
            )
            VALUES (?, ?, ?, ?)
        """, (
            "TM-R01",
            "Tirupati → Renigunta",
            "Tirupati Central Bus Stand",
            "Renigunta"
        ))

        route_id = cursor.lastrowid

        # -------------------------------------------------
        # DEFAULT STOPS
        # -------------------------------------------------

        stops = [

            (
                route_id,
                1,
                "Tirupati Central Bus Stand",
                13.6288,
                79.4192
            ),

            (
                route_id,
                2,
                "Railway Station",
                13.6287,
                79.4197
            ),

            (
                route_id,
                3,
                "Alipiri",
                13.6350,
                79.4100
            ),

            (
                route_id,
                4,
                "Renigunta",
                13.6510,
                79.5120
            )
        ]

        cursor.executemany("""
            INSERT INTO stops
            (
                route_id,
                stop_order,
                stop_name,
                latitude,
                longitude
            )
            VALUES (?, ?, ?, ?, ?)
        """, stops)

        # -------------------------------------------------
        # DEFAULT DEMO BUS
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO buses
            (
                bus_number,
                driver_name,
                route_id,
                status,
                latitude,
                longitude,
                current_stop,
                progress,
                started_at,
                trip_direction,
                trip_started
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "TM-101",
            "Demo Driver",
            route_id,
            "Available",
            13.6288,
            79.4192,
            1,
            0,
            None,
            "OUTBOUND",
            0
        ))

    connection.commit()
    connection.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor()

        try:

            cursor.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    password
                )
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                password
            ))

            connection.commit()
            connection.close()

            return redirect("/login")

        except sqlite3.IntegrityError:

            connection.close()

            return render_template(
                "register.html",
                error="This email is already registered."
            )

    return render_template("register.html")


# =========================================================
# USER LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                email
            FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            password
        ))

        user = cursor.fetchone()

        connection.close()

        if user:

            session.pop("admin_logged_in", None)
            session.pop("admin_username", None)

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_logged_in"):

        return redirect("/admin")

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and check_password_hash(
                ADMIN_PASSWORD_HASH,
                password
            )
        ):

            session.pop("user_id", None)
            session.pop("user_name", None)

            session["admin_logged_in"] = True
            session["admin_username"] = username

            return redirect("/admin")

        return render_template(
            "admin_login.html",
            error="Invalid admin username or password."
        )

    return render_template("admin_login.html")


# =========================================================
# USER DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect("/login")

    return render_template(
        "dashboard.html",
        name=session["user_name"]
    )


# =========================================================
# USER PROFILE
# =========================================================

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect("/login")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    ))

    user = cursor.fetchone()

    connection.close()

    if not user:

        session.clear()

        return redirect("/login")

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# CONTACT PAGE
# =========================================================

@app.route("/contact")
def contact():

    return render_template("contact.html")


# =========================================================
# PRIVACY POLICY
# =========================================================

@app.route("/privacy")
def privacy():

    return render_template("privacy_policy.html")


# =========================================================
# TERMS OF SERVICE
# =========================================================

@app.route("/terms")
def terms():

    return render_template("terms.html")


# =========================================================
# ROUTES PAGE
# =========================================================

@app.route("/routes")
def routes():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            route_number,
            route_name,
            start_location,
            destination
        FROM routes
        ORDER BY id
    """)

    route_rows = cursor.fetchall()

    routes = []

    for route in route_rows:

        cursor.execute("""
            SELECT
                id,
                bus_number,
                driver_name,
                status,
                latitude,
                longitude,
                current_stop,
                progress,
                trip_direction,
                trip_started
            FROM buses
            WHERE route_id = ?
            ORDER BY id
        """, (
            route["id"],
        ))

        buses = cursor.fetchall()

        routes.append({

            "id": route["id"],

            "route_number":
                route["route_number"],

            "route_name":
                route["route_name"],

            "start_location":
                route["start_location"],

            "destination":
                route["destination"],

            "buses":
                buses
        })

    connection.close()

    return render_template(
        "routes.html",
        routes=routes
    )


# =========================================================
# TRACK PAGE
# =========================================================

@app.route("/track")
def track():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("track.html")


# =========================================================
# ADMIN PAGE
# =========================================================

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # GET ALL BUSES
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            buses.id,
            buses.bus_number,
            buses.driver_name,
            buses.route_id,
            buses.status,
            buses.latitude,
            buses.longitude,
            buses.current_stop,
            buses.progress,
            buses.trip_direction,
            buses.trip_started,

            routes.route_number,
            routes.route_name,
            routes.start_location,
            routes.destination

        FROM buses

        JOIN routes
        ON buses.route_id = routes.id

        ORDER BY buses.id
    """)

    buses = cursor.fetchall()

    # -----------------------------------------------------
    # GET ALL ROUTES
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            route_number,
            route_name,
            start_location,
            destination
        FROM routes
        ORDER BY id
    """)

    routes = cursor.fetchall()

    connection.close()

    return render_template(
        "admin.html",
        buses=buses,
        routes=routes
    )


# =========================================================
# ADD BUS
# =========================================================

@app.route("/admin/add-bus", methods=["GET", "POST"])
def add_bus():

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        bus_number = request.form.get(
            "bus_number",
            ""
        ).strip().upper()

        driver_name = request.form.get(
            "driver_name",
            ""
        ).strip()

        route_id = request.form.get(
            "route_id",
            ""
        ).strip()

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not bus_number or not route_id:

            cursor.execute("""
                SELECT *
                FROM routes
                ORDER BY id
            """)

            routes = cursor.fetchall()

            connection.close()

            return render_template(
                "add_bus.html",
                routes=routes,
                error="Bus number and route are required."
            )

        # -------------------------------------------------
        # CHECK ROUTE
        # -------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM routes
            WHERE id = ?
        """, (
            route_id,
        ))

        route = cursor.fetchone()

        if not route:

            cursor.execute("""
                SELECT *
                FROM routes
                ORDER BY id
            """)

            routes = cursor.fetchall()

            connection.close()

            return render_template(
                "add_bus.html",
                routes=routes,
                error="Selected route does not exist."
            )

        # -------------------------------------------------
        # GET FIRST STOP
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                latitude,
                longitude
            FROM stops
            WHERE route_id = ?
            ORDER BY stop_order
            LIMIT 1
        """, (
            route_id,
        ))

        first_stop = cursor.fetchone()

        latitude = None
        longitude = None

        if first_stop:

            latitude = first_stop["latitude"]
            longitude = first_stop["longitude"]

        try:

            cursor.execute("""
                INSERT INTO buses
                (
                    bus_number,
                    driver_name,
                    route_id,
                    status,
                    latitude,
                    longitude,
                    current_stop,
                    progress,
                    started_at,
                    trip_direction,
                    trip_started
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bus_number,
                driver_name,
                route_id,
                "Available",
                latitude,
                longitude,
                1,
                0,
                None,
                "OUTBOUND",
                0
            ))

            connection.commit()
            connection.close()

            return redirect("/admin")

        except sqlite3.IntegrityError:

            cursor.execute("""
                SELECT *
                FROM routes
                ORDER BY id
            """)

            routes = cursor.fetchall()

            connection.close()

            return render_template(
                "add_bus.html",
                routes=routes,
                error="This bus number is already registered."
            )

    cursor.execute("""
        SELECT *
        FROM routes
        ORDER BY id
    """)

    routes = cursor.fetchall()

    connection.close()

    return render_template(
        "add_bus.html",
        routes=routes
    )


# =========================================================
# EDIT BUS
# =========================================================

@app.route(
    "/admin/edit-bus/<int:bus_id>",
    methods=["GET", "POST"]
)
def edit_bus(bus_id):

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # GET BUS
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            bus_number,
            driver_name,
            route_id,
            status,
            current_stop,
            trip_direction,
            trip_started
        FROM buses
        WHERE id = ?
    """, (
        bus_id,
    ))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        return redirect("/admin")

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        bus_number = request.form.get(
            "bus_number",
            ""
        ).strip().upper()

        driver_name = request.form.get(
            "driver_name",
            ""
        ).strip()

        route_id = request.form.get(
            "route_id",
            ""
        ).strip()

        if not bus_number or not route_id:

            cursor.execute("""
                SELECT *
                FROM routes
                ORDER BY id
            """)

            routes = cursor.fetchall()

            connection.close()

            return render_template(
                "edit_bus.html",
                bus=bus,
                routes=routes,
                error="Bus number and route are required."
            )

        # -------------------------------------------------
        # CHECK ROUTE
        # -------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM routes
            WHERE id = ?
        """, (
            route_id,
        ))

        route = cursor.fetchone()

        if not route:

            cursor.execute("""
                SELECT *
                FROM routes
                ORDER BY id
            """)

            routes = cursor.fetchall()

            connection.close()

            return render_template(
                "edit_bus.html",
                bus=bus,
                routes=routes,
                error="Selected route does not exist."
            )

        # -------------------------------------------------
        # IF ROUTE CHANGED
        # RESET BUS TO FIRST STOP
        # -------------------------------------------------

        route_changed = (
            str(bus["route_id"]) != str(route_id)
        )

        latitude = None
        longitude = None
        current_stop = bus["current_stop"] or 1
        progress = 0

        if route_changed:

            cursor.execute("""
                SELECT
                    latitude,
                    longitude
                FROM stops
                WHERE route_id = ?
                ORDER BY stop_order
                LIMIT 1
            """, (
                route_id,
            ))

            first_stop = cursor.fetchone()

            if first_stop:

                latitude = first_stop["latitude"]
                longitude = first_stop["longitude"]

            current_stop = 1
            progress = 0

        try:

            if route_changed:

                cursor.execute("""
                    UPDATE buses
                    SET
                        bus_number = ?,
                        driver_name = ?,
                        route_id = ?,
                        status = 'Available',
                        latitude = ?,
                        longitude = ?,
                        current_stop = 1,
                        progress = 0,
                        started_at = NULL,
                        trip_direction = 'OUTBOUND',
                        trip_started = 0
                    WHERE id = ?
                """, (
                    bus_number,
                    driver_name,
                    route_id,
                    latitude,
                    longitude,
                    bus_id
                ))

            else:

                cursor.execute("""
                    UPDATE buses
                    SET
                        bus_number = ?,
                        driver_name = ?
                    WHERE id = ?
                """, (
                    bus_number,
                    driver_name,
                    bus_id
                ))

            connection.commit()
            connection.close()

            return redirect("/admin")

        except sqlite3.IntegrityError:

            cursor.execute("""
                SELECT *
                FROM routes
                ORDER BY id
            """)

            routes = cursor.fetchall()

            connection.close()

            return render_template(
                "edit_bus.html",
                bus=bus,
                routes=routes,
                error="This bus number is already registered."
            )

    # -----------------------------------------------------
    # GET ROUTES
    # -----------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM routes
        ORDER BY id
    """)

    routes = cursor.fetchall()

    connection.close()

    return render_template(
        "edit_bus.html",
        bus=bus,
        routes=routes
    )


# =========================================================
# DELETE BUS
# =========================================================

@app.route(
    "/admin/delete-bus/<int:bus_id>",
    methods=["POST"]
)
def delete_bus(bus_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK BUS
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            bus_number,
            status,
            route_id
        FROM buses
        WHERE id = ?
    """, (
        bus_id,
    ))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        return redirect(
            "/admin?error=Bus not found."
        )

    # -----------------------------------------------------
    # DO NOT DELETE ACTIVE BUS
    # -----------------------------------------------------

    if bus["status"] == "Active":

        connection.close()

        return redirect(
            "/admin?error="
            + f"Bus {bus['bus_number']} is currently active. "
              f"Stop the bus before deleting it."
        )

    # -----------------------------------------------------
    # DELETE BUS
    # -----------------------------------------------------

    cursor.execute("""
        DELETE FROM buses
        WHERE id = ?
    """, (
        bus_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        "/admin?success="
        + f"Bus {bus['bus_number']} deleted successfully."
    )


# =========================================================
# ADD ROUTE
# =========================================================

@app.route(
    "/admin/add-route",
    methods=["GET", "POST"]
)
def add_route():

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    if request.method == "POST":

        route_number = request.form.get(
            "route_number",
            ""
        ).strip().upper()

        route_name = request.form.get(
            "route_name",
            ""
        ).strip()

        start_location = request.form.get(
            "start_location",
            ""
        ).strip()

        destination = request.form.get(
            "destination",
            ""
        ).strip()

        # -------------------------------------------------
        # STOP DATA
        # -------------------------------------------------

        stop_names = request.form.getlist(
            "stop_name[]"
        )

        stop_latitudes = request.form.getlist(
            "latitude[]"
        )

        stop_longitudes = request.form.getlist(
            "longitude[]"
        )

        # Support forms using names without []
        if not stop_names:

            stop_names = request.form.getlist(
                "stop_name"
            )

        if not stop_latitudes:

            stop_latitudes = request.form.getlist(
                "latitude"
            )

        if not stop_longitudes:

            stop_longitudes = request.form.getlist(
                "longitude"
            )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if (
            not route_number
            or not route_name
            or not start_location
            or not destination
        ):

            return render_template(
                "add_route.html",
                error="Please fill in all route details."
            )

        if len(stop_names) < 2:

            return render_template(
                "add_route.html",
                error="A route must have at least 2 stops."
            )

        connection = get_connection()
        cursor = connection.cursor()

        try:

            # -------------------------------------------------
            # INSERT ROUTE
            # -------------------------------------------------

            cursor.execute("""
                INSERT INTO routes
                (
                    route_number,
                    route_name,
                    start_location,
                    destination
                )
                VALUES (?, ?, ?, ?)
            """, (
                route_number,
                route_name,
                start_location,
                destination
            ))

            route_id = cursor.lastrowid

            # -------------------------------------------------
            # INSERT STOPS
            # -------------------------------------------------

            for index, stop_name in enumerate(stop_names):

                stop_name = stop_name.strip()

                if not stop_name:
                    continue

                try:

                    latitude = float(
                        stop_latitudes[index]
                    )

                    longitude = float(
                        stop_longitudes[index]
                    )

                except (
                    ValueError,
                    IndexError
                ):

                    connection.rollback()
                    connection.close()

                    return render_template(
                        "add_route.html",
                        error="Please enter valid latitude and longitude values for every stop."
                    )

                cursor.execute("""
                    INSERT INTO stops
                    (
                        route_id,
                        stop_order,
                        stop_name,
                        latitude,
                        longitude
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    route_id,
                    index + 1,
                    stop_name,
                    latitude,
                    longitude
                ))

            connection.commit()
            connection.close()

            return redirect("/admin")

        except sqlite3.IntegrityError:

            connection.rollback()
            connection.close()

            return render_template(
                "add_route.html",
                error="This route number is already registered."
            )

    return render_template(
        "add_route.html"
    )


# =========================================================
# EDIT ROUTE
# =========================================================

@app.route(
    "/admin/edit-route/<int:route_id>",
    methods=["GET", "POST"]
)
def edit_route(route_id):

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # GET ROUTE
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            route_number,
            route_name,
            start_location,
            destination
        FROM routes
        WHERE id = ?
    """, (
        route_id,
    ))

    route = cursor.fetchone()

    if not route:

        connection.close()

        return redirect("/admin")

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        route_number = request.form.get(
            "route_number",
            ""
        ).strip().upper()

        route_name = request.form.get(
            "route_name",
            ""
        ).strip()

        start_location = request.form.get(
            "start_location",
            ""
        ).strip()

        destination = request.form.get(
            "destination",
            ""
        ).strip()

        stop_names = request.form.getlist(
            "stop_name[]"
        )

        stop_latitudes = request.form.getlist(
            "latitude[]"
        )

        stop_longitudes = request.form.getlist(
            "longitude[]"
        )

        if not stop_names:

            stop_names = request.form.getlist(
                "stop_name"
            )

        if not stop_latitudes:

            stop_latitudes = request.form.getlist(
                "latitude"
            )

        if not stop_longitudes:

            stop_longitudes = request.form.getlist(
                "longitude"
            )

        if (
            not route_number
            or not route_name
            or not start_location
            or not destination
        ):

            cursor.execute("""
                SELECT *
                FROM stops
                WHERE route_id = ?
                ORDER BY stop_order
            """, (
                route_id,
            ))

            stops = cursor.fetchall()

            connection.close()

            return render_template(
                "edit_route.html",
                route=route,
                stops=stops,
                error="Please fill in all route details."
            )

        if len(stop_names) < 2:

            cursor.execute("""
                SELECT *
                FROM stops
                WHERE route_id = ?
                ORDER BY stop_order
            """, (
                route_id,
            ))

            stops = cursor.fetchall()

            connection.close()

            return render_template(
                "edit_route.html",
                route=route,
                stops=stops,
                error="A route must have at least 2 stops."
            )

        try:

            # -------------------------------------------------
            # UPDATE ROUTE
            # -------------------------------------------------

            cursor.execute("""
                UPDATE routes
                SET
                    route_number = ?,
                    route_name = ?,
                    start_location = ?,
                    destination = ?
                WHERE id = ?
            """, (
                route_number,
                route_name,
                start_location,
                destination,
                route_id
            ))

            # -------------------------------------------------
            # REMOVE OLD STOPS
            # -------------------------------------------------

            cursor.execute("""
                DELETE FROM stops
                WHERE route_id = ?
            """, (
                route_id,
            ))

            # -------------------------------------------------
            # INSERT UPDATED STOPS
            # -------------------------------------------------

            valid_stop_order = 1

            for index, stop_name in enumerate(stop_names):

                stop_name = stop_name.strip()

                if not stop_name:
                    continue

                try:

                    latitude = float(
                        stop_latitudes[index]
                    )

                    longitude = float(
                        stop_longitudes[index]
                    )

                except (
                    ValueError,
                    IndexError
                ):

                    connection.rollback()

                    cursor.execute("""
                        SELECT *
                        FROM stops
                        WHERE route_id = ?
                        ORDER BY stop_order
                    """, (
                        route_id,
                    ))

                    stops = cursor.fetchall()

                    connection.close()

                    return render_template(
                        "edit_route.html",
                        route=route,
                        stops=stops,
                        error="Please enter valid latitude and longitude values for every stop."
                    )

                cursor.execute("""
                    INSERT INTO stops
                    (
                        route_id,
                        stop_order,
                        stop_name,
                        latitude,
                        longitude
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    route_id,
                    valid_stop_order,
                    stop_name,
                    latitude,
                    longitude
                ))

                valid_stop_order += 1

            # -------------------------------------------------
            # RESET BUSES ASSIGNED TO THIS ROUTE
            #
            # Since stops may have changed, reset their
            # location to the first stop.
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    latitude,
                    longitude
                FROM stops
                WHERE route_id = ?
                ORDER BY stop_order
                LIMIT 1
            """, (
                route_id,
            ))

            first_stop = cursor.fetchone()

            if first_stop:

                cursor.execute("""
                    UPDATE buses
                    SET
                        status = 'Available',
                        latitude = ?,
                        longitude = ?,
                        current_stop = 1,
                        progress = 0,
                        started_at = NULL,
                        trip_direction = 'OUTBOUND',
                        trip_started = 0
                    WHERE route_id = ?
                """, (
                    first_stop["latitude"],
                    first_stop["longitude"],
                    route_id
                ))

            connection.commit()
            connection.close()

            return redirect("/admin")

        except sqlite3.IntegrityError:

            connection.rollback()

            cursor.execute("""
                SELECT *
                FROM stops
                WHERE route_id = ?
                ORDER BY stop_order
            """, (
                route_id,
            ))

            stops = cursor.fetchall()

            connection.close()

            return render_template(
                "edit_route.html",
                route=route,
                stops=stops,
                error="This route number is already registered."
            )

    # -----------------------------------------------------
    # GET STOPS
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            route_id,
            stop_order,
            stop_name,
            latitude,
            longitude
        FROM stops
        WHERE route_id = ?
        ORDER BY stop_order
    """, (
        route_id,
    ))

    stops = cursor.fetchall()

    connection.close()

    return render_template(
        "edit_route.html",
        route=route,
        stops=stops
    )


# =========================================================
# DELETE ROUTE
# =========================================================

@app.route(
    "/admin/delete-route/<int:route_id>",
    methods=["POST"]
)
def delete_route(route_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK ROUTE
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            route_number,
            route_name
        FROM routes
        WHERE id = ?
    """, (
        route_id,
    ))

    route = cursor.fetchone()

    if not route:

        connection.close()

        return redirect(
            "/admin?error=Route not found."
        )

    # -----------------------------------------------------
    # CHECK ASSIGNED BUSES
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            bus_number
        FROM buses
        WHERE route_id = ?
        ORDER BY bus_number
    """, (
        route_id,
    ))

    assigned_buses = cursor.fetchall()

    # -----------------------------------------------------
    # DO NOT DELETE ROUTE IF BUSES ARE ASSIGNED
    # -----------------------------------------------------

    if assigned_buses:

        bus_numbers = ", ".join(
            bus["bus_number"]
            for bus in assigned_buses
        )

        connection.close()

        return redirect(
            "/admin?error="
            + f"Cannot delete route {route['route_number']}. "
              f"The following buses are still assigned to it: "
              f"{bus_numbers}. "
              f"Delete or reassign these buses first."
        )

    # -----------------------------------------------------
    # DELETE ROUTE
    #
    # Stops are automatically deleted because of
    # ON DELETE CASCADE.
    # -----------------------------------------------------

    cursor.execute("""
        DELETE FROM routes
        WHERE id = ?
    """, (
        route_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        "/admin?success="
        + f"Route {route['route_number']} deleted successfully."
    )


# =========================================================
# START / RETURN BUS
# =========================================================

@app.route(
    "/admin/start-bus/<int:bus_id>",
    methods=["POST"]
)
def start_bus(bus_id):

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            route_id,
            status,
            current_stop,
            trip_direction
        FROM buses
        WHERE id = ?
    """, (
        bus_id,
    ))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        return redirect("/admin")

    if bus["status"] == "Active":

        connection.close()

        return redirect("/admin")

    cursor.execute("""
        SELECT
            stop_order,
            stop_name,
            latitude,
            longitude
        FROM stops
        WHERE route_id = ?
        ORDER BY stop_order
    """, (
        bus["route_id"],
    ))

    stops = cursor.fetchall()

    if len(stops) < 2:

        connection.close()

        return redirect("/admin")

    total_stops = len(stops)

    current_stop = bus["current_stop"] or 1

    if current_stop <= 1:

        direction = "OUTBOUND"

        starting_stop = stops[0]

    elif current_stop >= total_stops:

        direction = "RETURN"

        starting_stop = stops[-1]

    else:

        if bus["trip_direction"] == "RETURN":

            direction = "RETURN"

            starting_stop = stops[
                current_stop - 1
            ]

        else:

            direction = "OUTBOUND"

            starting_stop = stops[
                current_stop - 1
            ]

    cursor.execute("""
        UPDATE buses
        SET
            status = 'Active',
            latitude = ?,
            longitude = ?,
            current_stop = ?,
            progress = 0,
            started_at = ?,
            trip_direction = ?,
            trip_started = 1
        WHERE id = ?
    """, (
        starting_stop["latitude"],
        starting_stop["longitude"],
        starting_stop["stop_order"],
        time.time(),
        direction,
        bus_id
    ))

    connection.commit()
    connection.close()

    return redirect("/admin")


# =========================================================
# STOP BUS MANUALLY
# =========================================================

@app.route(
    "/admin/stop-bus/<int:bus_id>",
    methods=["POST"]
)
def stop_bus(bus_id):

    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK BUS
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            bus_number,
            status
        FROM buses
        WHERE id = ?
    """, (
        bus_id,
    ))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        return redirect(
            "/admin?error=Bus not found."
        )

    # -----------------------------------------------------
    # CHECK CURRENT STATUS
    # -----------------------------------------------------

    if bus["status"] != "Active":

        connection.close()

        return redirect(
            "/admin?error="
            + f"Bus {bus['bus_number']} is not currently running."
        )

    # -----------------------------------------------------
    # STOP BUS
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE buses
        SET
            status = 'Available',
            started_at = NULL
        WHERE id = ?
    """, (
        bus_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        "/admin?success="
        + f"Bus {bus['bus_number']} stopped successfully."
    )


# =========================================================
# BUS STATE CALCULATION
# =========================================================

def calculate_bus_state(bus, stops):

    total_stops = len(stops)

    if total_stops == 0:

        return {
            "latitude": bus["latitude"],
            "longitude": bus["longitude"],
            "current_stop": 1,
            "progress": 0,
            "destination_reached": False
        }

    current_stop = bus["current_stop"] or 1

    current_stop = max(
        1,
        min(
            total_stops,
            int(current_stop)
        )
    )

    progress = bus["progress"] or 0

    progress = max(
        0,
        min(
            1,
            float(progress)
        )
    )

    direction = (
        bus["trip_direction"]
        or "OUTBOUND"
    )

    latitude = bus["latitude"]
    longitude = bus["longitude"]

    if latitude is None or longitude is None:

        stop = stops[current_stop - 1]

        latitude = stop["latitude"]
        longitude = stop["longitude"]

    destination_reached = False

    if (
        bus["status"] == "Available"
        and bus["trip_started"] == 1
    ):

        if (
            direction == "OUTBOUND"
            and current_stop >= total_stops
        ):

            destination_reached = True

        elif (
            direction == "RETURN"
            and current_stop <= 1
        ):

            destination_reached = True

    return {
        "latitude": latitude,
        "longitude": longitude,
        "current_stop": current_stop,
        "progress": progress,
        "destination_reached": destination_reached
    }


# =========================================================
# GET SINGLE BUS
# =========================================================

@app.route("/api/bus/<bus_number>")
def get_bus(bus_number):

    bus_number = bus_number.strip().upper()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            buses.id,
            buses.bus_number,
            buses.driver_name,
            buses.route_id,
            buses.status,
            buses.latitude,
            buses.longitude,
            buses.current_stop,
            buses.progress,
            buses.started_at,
            buses.trip_direction,
            buses.trip_started,

            routes.route_number,
            routes.route_name,
            routes.start_location,
            routes.destination

        FROM buses

        JOIN routes
        ON buses.route_id = routes.id

        WHERE buses.bus_number = ?
    """, (
        bus_number,
    ))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Bus not found."
        }), 404

    cursor.execute("""
        SELECT
            stop_order,
            stop_name,
            latitude,
            longitude
        FROM stops
        WHERE route_id = ?
        ORDER BY stop_order
    """, (
        bus["route_id"],
    ))

    stops = cursor.fetchall()

    state = calculate_bus_state(
        bus,
        stops
    )

    total_stops = len(stops)

    current_stop = state["current_stop"]

    progress = state["progress"]

    direction = (
        bus["trip_direction"]
        or "OUTBOUND"
    )

    destination_reached = (
        state["destination_reached"]
    )

    if total_stops > 0:

        current_stop_data = stops[
            current_stop - 1
        ]

    else:

        current_stop_data = None

    if direction == "RETURN":

        start_location = stops[-1]["stop_name"]

        destination = stops[0]["stop_name"]

    else:

        start_location = stops[0]["stop_name"]

        destination = stops[-1]["stop_name"]

    display_route = (
        f"{start_location} → {destination}"
    )

    next_stop = None

    if bus["status"] == "Active":

        if direction == "OUTBOUND":

            if current_stop < total_stops:

                next_stop = stops[
                    current_stop
                ]

        else:

            if current_stop > 1:

                next_stop = stops[
                    current_stop - 2
                ]

    if destination_reached:

        eta = "Arrived"

    elif bus["status"] != "Active":

        eta = "Not running"

    else:

        if direction == "OUTBOUND":

            remaining_segments = (
                total_stops
                - current_stop
                - 1
            )

        else:

            remaining_segments = (
                current_stop
                - 2
            )

        remaining_segments = max(
            0,
            remaining_segments
        )

        current_remaining = (
            (1 - progress)
            * SEGMENT_TIME
        )

        remaining_seconds = (
            current_remaining
            +
            remaining_segments
            * SEGMENT_TIME
        )

        eta_minutes = max(
            1,
            int(
                (remaining_seconds + 59)
                // 60
            )
        )

        eta = f"{eta_minutes} minutes"

    if total_stops <= 1:

        overall_progress = 100

    elif direction == "OUTBOUND":

        overall_progress = (
            (
                (current_stop - 1)
                +
                progress
            )
            /
            (total_stops - 1)
        ) * 100

    else:

        overall_progress = (
            (
                (total_stops - current_stop)
                +
                progress
            )
            /
            (total_stops - 1)
        ) * 100

    overall_progress = max(
        0,
        min(
            100,
            overall_progress
        )
    )

    if destination_reached:

        overall_progress = 100

    connection.close()

    return jsonify({

        "success": True,

        "bus": {

            "id":
                bus["id"],

            "bus_number":
                bus["bus_number"],

            "driver_name":
                bus["driver_name"],

            "status":
                bus["status"],

            "latitude":
                state["latitude"],

            "longitude":
                state["longitude"],

            "current_stop":
                current_stop,

            "current_stop_name": (
                current_stop_data["stop_name"]
                if current_stop_data
                else None
            ),

            "progress":
                progress,

            "progress_percentage":
                round(
                    overall_progress,
                    1
                ),

            "total_stops":
                total_stops,

            "route_number":
                bus["route_number"],

            "route_name":
                display_route,

            "start_location":
                start_location,

            "destination":
                destination,

            "eta":
                eta,

            "destination_reached":
                destination_reached,

            "trip_direction":
                direction,

            "trip_started":
                bool(
                    bus["trip_started"]
                )
        },

        "current_stop": {

            "stop_order":
                current_stop,

            "stop_name": (
                current_stop_data["stop_name"]
                if current_stop_data
                else destination
            )
        },

        "next_stop": (

            {

                "stop_order":
                    next_stop["stop_order"],

                "stop_name":
                    next_stop["stop_name"],

                "latitude":
                    next_stop["latitude"],

                "longitude":
                    next_stop["longitude"]
            }

            if next_stop

            else None
        ),

        "stops": [

            {

                "stop_order":
                    stop["stop_order"],

                "stop_name":
                    stop["stop_name"],

                "latitude":
                    stop["latitude"],

                "longitude":
                    stop["longitude"]

            }

            for stop in stops

        ],

        "total_stops":
            total_stops
    })


# =========================================================
# GET ALL BUSES
# =========================================================

@app.route("/api/buses")
def get_buses():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            buses.id,
            buses.bus_number,
            buses.driver_name,
            buses.route_id,
            buses.status,
            buses.latitude,
            buses.longitude,
            buses.current_stop,
            buses.progress,
            buses.started_at,
            buses.trip_direction,
            buses.trip_started,

            routes.route_number,
            routes.route_name,
            routes.start_location,
            routes.destination

        FROM buses

        JOIN routes
        ON buses.route_id = routes.id

        ORDER BY buses.id
    """)

    buses = cursor.fetchall()

    result = []

    for bus in buses:

        cursor.execute("""
            SELECT
                stop_order,
                stop_name,
                latitude,
                longitude
            FROM stops
            WHERE route_id = ?
            ORDER BY stop_order
        """, (
            bus["route_id"],
        ))

        stops = cursor.fetchall()

        state = calculate_bus_state(
            bus,
            stops
        )

        direction = (
            bus["trip_direction"]
            or "OUTBOUND"
        )

        total_stops = len(stops)

        if total_stops > 0:

            if direction == "RETURN":

                start_location = (
                    stops[-1]["stop_name"]
                )

                destination = (
                    stops[0]["stop_name"]
                )

            else:

                start_location = (
                    stops[0]["stop_name"]
                )

                destination = (
                    stops[-1]["stop_name"]
                )

        else:

            start_location = "Unknown"

            destination = "Unknown"

        route_name = (
            f"{start_location} → {destination}"
        )

        current_stop = state["current_stop"]

        current_stop_name = None

        if total_stops > 0:

            current_stop_name = (
                stops[current_stop - 1]["stop_name"]
            )

        next_stop = None

        if bus["status"] == "Active":

            if direction == "OUTBOUND":

                if current_stop < total_stops:

                    next_stop = stops[
                        current_stop
                    ]

            else:

                if current_stop > 1:

                    next_stop = stops[
                        current_stop - 2
                    ]

        next_stop_name = (
            next_stop["stop_name"]
            if next_stop
            else None
        )

        progress = state["progress"]

        if total_stops <= 1:

            overall_progress = 100

        elif direction == "OUTBOUND":

            overall_progress = (
                (
                    (current_stop - 1)
                    +
                    progress
                )
                /
                (total_stops - 1)
            ) * 100

        else:

            overall_progress = (
                (
                    (total_stops - current_stop)
                    +
                    progress
                )
                /
                (total_stops - 1)
            ) * 100

        overall_progress = max(
            0,
            min(
                100,
                overall_progress
            )
        )

        if state["destination_reached"]:

            overall_progress = 100

        if state["destination_reached"]:

            eta = "Arrived"

        elif bus["status"] != "Active":

            eta = "Not running"

        else:

            if direction == "OUTBOUND":

                remaining_segments = (
                    total_stops
                    - current_stop
                    - 1
                )

            else:

                remaining_segments = (
                    current_stop
                    - 2
                )

            remaining_segments = max(
                0,
                remaining_segments
            )

            current_remaining = (
                (1 - progress)
                * SEGMENT_TIME
            )

            remaining_seconds = (
                current_remaining
                +
                remaining_segments
                * SEGMENT_TIME
            )

            eta_minutes = max(
                1,
                int(
                    (remaining_seconds + 59)
                    // 60
                )
            )

            eta = f"{eta_minutes} minutes"

        result.append({

            "id":
                bus["id"],

            "bus_number":
                bus["bus_number"],

            "driver_name":
                bus["driver_name"],

            "status":
                bus["status"],

            "latitude":
                state["latitude"],

            "longitude":
                state["longitude"],

            "current_stop":
                current_stop,

            "current_stop_name":
                current_stop_name,

            "next_stop_name":
                next_stop_name,

            "progress":
                progress,

            "progress_percentage":
                round(
                    overall_progress,
                    1
                ),

            "total_stops":
                total_stops,

            "route_number":
                bus["route_number"],

            "route_name":
                route_name,

            "start_location":
                start_location,

            "destination":
                destination,

            "eta":
                eta,

            "trip_direction":
                direction,

            "trip_started":
                bool(
                    bus["trip_started"]
                ),

            "destination_reached":
                state["destination_reached"]
        })

    connection.close()

    return jsonify({

        "success": True,

        "buses": result
    })


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    session.pop(
        "admin_username",
        None
    )

    return redirect("/admin/login")


# =========================================================
# NORMAL USER LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
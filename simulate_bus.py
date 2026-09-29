import sqlite3
import time


# =========================================================
# SETTINGS
# =========================================================

DATABASE = "database.db"

# Same as app.py
SEGMENT_TIME = 300

# Progress added every second
PROGRESS_STEP = 1 / SEGMENT_TIME

# Simulator update interval
UPDATE_INTERVAL = 1


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# GET ALL ACTIVE BUSES
# =========================================================

def get_active_buses():

    connection = get_connection()
    cursor = connection.cursor()

    # IMPORTANT:
    # Do NOT require trip_started = 1 here.
    # Any bus whose status is Active should move.
    cursor.execute("""
        SELECT
            id,
            bus_number,
            route_id,
            status,
            current_stop,
            progress,
            trip_direction,
            trip_started
        FROM buses
        WHERE status = 'Active'
        ORDER BY id
    """)

    buses = cursor.fetchall()

    connection.close()

    return buses


# =========================================================
# GET ROUTE STOPS
# =========================================================

def get_route_stops(route_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            stop_order,
            stop_name,
            latitude,
            longitude
        FROM stops
        WHERE route_id = ?
        ORDER BY stop_order
    """, (route_id,))

    stops = cursor.fetchall()

    connection.close()

    return stops


# =========================================================
# UPDATE BUS POSITION
# =========================================================

def update_bus_position(
    bus_id,
    latitude,
    longitude,
    current_stop,
    progress
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE buses
        SET
            latitude = ?,
            longitude = ?,
            current_stop = ?,
            progress = ?
        WHERE id = ?
        AND status = 'Active'
    """, (
        latitude,
        longitude,
        current_stop,
        progress,
        bus_id
    ))

    connection.commit()
    connection.close()


# =========================================================
# MARK BUS AVAILABLE
# =========================================================

def mark_bus_available(
    bus_id,
    destination_stop,
    direction
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE buses
        SET
            status = 'Available',
            latitude = ?,
            longitude = ?,
            current_stop = ?,
            progress = 0,
            started_at = NULL,
            trip_started = 0,
            trip_direction = ?
        WHERE id = ?
    """, (
        destination_stop["latitude"],
        destination_stop["longitude"],
        destination_stop["stop_order"],
        direction,
        bus_id
    ))

    connection.commit()
    connection.close()


# =========================================================
# MOVE ONE BUS
# =========================================================

def move_bus(bus):

    bus_id = bus["id"]
    bus_number = bus["bus_number"]
    route_id = bus["route_id"]

    direction = (
        bus["trip_direction"]
        or "OUTBOUND"
    )

    direction = direction.upper()

    if direction not in ("OUTBOUND", "RETURN"):
        direction = "OUTBOUND"

    # -----------------------------------------------------
    # GET ROUTE STOPS
    # -----------------------------------------------------

    stops = get_route_stops(route_id)

    if len(stops) < 2:

        print(
            f"{bus_number}: "
            f"Route does not contain enough stops."
        )

        return

    total_stops = len(stops)

    # -----------------------------------------------------
    # CURRENT STOP
    # -----------------------------------------------------

    try:

        current_stop = int(
            bus["current_stop"] or 1
        )

    except (TypeError, ValueError):

        current_stop = 1

    current_stop = max(
        1,
        min(
            total_stops,
            current_stop
        )
    )

    # -----------------------------------------------------
    # CURRENT SEGMENT PROGRESS
    # -----------------------------------------------------

    try:

        progress = float(
            bus["progress"] or 0
        )

    except (TypeError, ValueError):

        progress = 0.0

    progress = max(
        0.0,
        min(
            1.0,
            progress
        )
    )

    # =====================================================
    # OUTBOUND
    #
    # 1 -> 2
    # 2 -> 3
    # 3 -> 4
    # =====================================================

    if direction == "OUTBOUND":

        # Already at final destination
        if current_stop >= total_stops:

            mark_bus_available(
                bus_id,
                stops[-1],
                direction
            )

            print(
                f"✓ {bus_number} reached "
                f"{stops[-1]['stop_name']}"
            )

            print(
                f"✓ {bus_number} is now AVAILABLE"
            )

            return

        start_index = current_stop - 1
        end_index = current_stop

    # =====================================================
    # RETURN
    #
    # 4 -> 3
    # 3 -> 2
    # 2 -> 1
    # =====================================================

    else:

        # Already at starting destination
        if current_stop <= 1:

            mark_bus_available(
                bus_id,
                stops[0],
                direction
            )

            print(
                f"✓ {bus_number} reached "
                f"{stops[0]['stop_name']}"
            )

            print(
                f"✓ {bus_number} is now AVAILABLE"
            )

            return

        start_index = current_stop - 1
        end_index = current_stop - 2

    # -----------------------------------------------------
    # START / END STOPS
    # -----------------------------------------------------

    start_stop = stops[start_index]
    end_stop = stops[end_index]

    # -----------------------------------------------------
    # INCREASE PROGRESS
    # -----------------------------------------------------

    progress += PROGRESS_STEP

    # =====================================================
    # SEGMENT COMPLETED
    # =====================================================

    if progress >= 1.0:

        progress = 0.0

        new_current_stop = int(
            end_stop["stop_order"]
        )

        # -------------------------------------------------
        # OUTBOUND DESTINATION
        # -------------------------------------------------

        if (
            direction == "OUTBOUND"
            and new_current_stop >= total_stops
        ):

            update_bus_position(
                bus_id,
                float(end_stop["latitude"]),
                float(end_stop["longitude"]),
                new_current_stop,
                0
            )

            mark_bus_available(
                bus_id,
                stops[-1],
                direction
            )

            print()
            print(
                f"✓ {bus_number} reached "
                f"{stops[-1]['stop_name']}"
            )
            print(
                f"✓ {bus_number} is now AVAILABLE"
            )
            print()

            return

        # -------------------------------------------------
        # RETURN DESTINATION
        # -------------------------------------------------

        if (
            direction == "RETURN"
            and new_current_stop <= 1
        ):

            update_bus_position(
                bus_id,
                float(end_stop["latitude"]),
                float(end_stop["longitude"]),
                new_current_stop,
                0
            )

            mark_bus_available(
                bus_id,
                stops[0],
                direction
            )

            print()
            print(
                f"✓ {bus_number} reached "
                f"{stops[0]['stop_name']}"
            )
            print(
                f"✓ {bus_number} is now AVAILABLE"
            )
            print()

            return

        # -------------------------------------------------
        # REACHED INTERMEDIATE STOP
        # -------------------------------------------------

        update_bus_position(
            bus_id,
            float(end_stop["latitude"]),
            float(end_stop["longitude"]),
            new_current_stop,
            0
        )

        print(
            f"{bus_number} reached "
            f"{end_stop['stop_name']}"
        )

        return

    # =====================================================
    # CALCULATE LIVE GPS POSITION
    # =====================================================

    start_lat = float(
        start_stop["latitude"]
    )

    start_lon = float(
        start_stop["longitude"]
    )

    end_lat = float(
        end_stop["latitude"]
    )

    end_lon = float(
        end_stop["longitude"]
    )

    latitude = (
        start_lat
        +
        (
            end_lat - start_lat
        )
        *
        progress
    )

    longitude = (
        start_lon
        +
        (
            end_lon - start_lon
        )
        *
        progress
    )

    # =====================================================
    # SAVE POSITION
    # =====================================================

    update_bus_position(
        bus_id,
        latitude,
        longitude,
        current_stop,
        progress
    )

    print(
        f"{bus_number} | "
        f"{direction} | "
        f"{start_stop['stop_name']} -> "
        f"{end_stop['stop_name']} | "
        f"{progress * 100:.0f}% | "
        f"{latitude:.6f}, "
        f"{longitude:.6f}"
    )


# =========================================================
# MAIN SIMULATOR
# =========================================================

def main():

    print()
    print("=" * 60)
    print(" TrackMove Multi-Bus GPS Simulator")
    print("=" * 60)
    print()

    print("Monitoring ALL ACTIVE buses...")
    print()

    print(
        "OUTBOUND : Tirupati → Renigunta"
    )

    print(
        "RETURN   : Renigunta → Tirupati"
    )

    print()
    print("Waiting for buses...")
    print()

    while True:

        try:

            # -------------------------------------------------
            # GET ALL ACTIVE BUSES
            # -------------------------------------------------

            active_buses = get_active_buses()

            # -------------------------------------------------
            # NO ACTIVE BUSES
            # -------------------------------------------------

            if not active_buses:

                time.sleep(
                    UPDATE_INTERVAL
                )

                continue

            # -------------------------------------------------
            # MOVE EVERY ACTIVE BUS
            # -------------------------------------------------

            print(
                f"Active buses: "
                f"{len(active_buses)}"
            )

            for bus in active_buses:

                try:

                    move_bus(bus)

                except Exception as error:

                    print(
                        f"ERROR moving "
                        f"{bus['bus_number']}: "
                        f"{error}"
                    )

            # -------------------------------------------------
            # WAIT
            # -------------------------------------------------

            time.sleep(
                UPDATE_INTERVAL
            )

        except KeyboardInterrupt:

            print()
            print(
                "Simulator stopped."
            )

            break

        except Exception as error:

            print(
                "Simulator error:",
                error
            )

            time.sleep(2)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
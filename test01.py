def get_gps_data():
    """Get GPS data including speed, bearing, and battery level from gpsLocation and deviceState messages."""
    global previous_lat, previous_lon

    gps_socket = messaging.sub_sock("gpsLocation", conflate=True)
    msg = messaging.recv_one_or_none(gps_socket)

    if msg is not None:
        gps = msg.gpsLocation
        latitude = gps.latitude
        longitude = gps.longitude
        altitude = gps.altitude
        speed = gps.speed
        bearing = gps.bearingDeg
        accuracy = gps.horizontalAccuracy
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Extract velocity components (vNED - North, East, Down)
        vel_n, vel_e, vel_d = gps.vNED

        # If no bearing is available from gpsLocation, calculate it using the previous position
        if bearing is None or bearing == 0:
            if previous_lat is not None and previous_lon is not None:
                bearing = GPSHandler.calculate_bearing(
                    previous_lat, previous_lon, latitude, longitude
                )
            else:
                bearing = None  # Bearing not available if no previous point exists

        # Update previous GPS position
        previous_lat = latitude
        previous_lon = longitude

        # Calculate speed from velocity components (Pythagorean theorem) if needed
        calculated_speed = (vel_n**2 + vel_e**2 + vel_d**2) ** 0.5

        # Choose speed from gpsLocation or calculate it if not present
        final_speed = speed if speed is not None and speed > 0 else calculated_speed

        # Get battery level
        battery_level = GPSHandler.get_battery_level()

        return (
            latitude,
            longitude,
            altitude,
            accuracy,
            timestamp,
            final_speed,
            bearing,
            battery_level,
        )
    return None

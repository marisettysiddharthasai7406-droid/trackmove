"use strict";

/*
=========================================================
TRACKMOVE - LIVE BUS TRACKING
=========================================================
Default:
    Shows ALL buses on the map.

When a bus is selected:
    Shows selected bus details + route + stops.

When selection is cleared:
    Returns to ALL buses mode.
=========================================================
*/


/* =========================================================
   GLOBAL VARIABLES
========================================================= */

let currentMarker = null;
let selectedBus = null;
let liveTimer = null;
let allBusesTimer = null;
let routeLine = null;
let stopMarkers = [];
let lastPosition = null;
let animationFrame = null;

let allBusMarkers = {};
let allBusData = [];


/* =========================================================
   MAP
========================================================= */

const map = L.map("trackingMap").setView(
    [13.6288, 79.4192],
    13
);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


/* =========================================================
   BUS ICON
========================================================= */

function createBusIcon(bus) {

    let background = "#1769aa";

    if (bus.status === "Available") {
        background = "#16865b";
    }

    if (
        bus.status === "Active" &&
        bus.trip_direction === "RETURN"
    ) {
        background = "#6842a5";
    }

    return L.divIcon({
        className: "tracking-bus-marker",

        html:
            '<div style="' +
            'width:42px;' +
            'height:42px;' +
            'border-radius:50%;' +
            'background:' + background + ';' +
            'border:3px solid white;' +
            'box-shadow:0 3px 12px rgba(0,0,0,0.30);' +
            'display:flex;' +
            'align-items:center;' +
            'justify-content:center;' +
            'font-size:21px;' +
            '">' +
            '🚌' +
            '</div>',

        iconSize: [42, 42],
        iconAnchor: [21, 21]
    });
}


/* =========================================================
   STOP ICON
========================================================= */

function createStopIcon(type) {

    let color = "#777";

    if (type === "reached") {
        color = "#16a34a";
    }

    if (type === "next") {
        color = "#2563eb";
    }

    if (type === "destination") {
        color = "#dc2626";
    }

    if (type === "start") {
        color = "#9333ea";
    }

    return L.divIcon({
        className: "custom-stop-marker",

        html:
            '<div style="' +
            'width:22px;' +
            'height:22px;' +
            'border-radius:50%;' +
            'background:' + color + ';' +
            'border:3px solid white;' +
            'box-shadow:0 2px 8px rgba(0,0,0,0.35);' +
            '"></div>',

        iconSize: [22, 22],
        iconAnchor: [11, 11]
    });
}


/* =========================================================
   LOAD BUS LIST
========================================================= */

async function loadBusList() {

    const busSearch =
        document.getElementById("busSearch");

    if (!busSearch) {
        return;
    }

    try {

        const response = await fetch(
            "/api/buses",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            busSearch.innerHTML =
                '<option value="">Unable to load buses</option>';

            return;
        }

        const buses = data.buses || [];

        allBusData = buses;

        busSearch.innerHTML =
            '<option value="">Select a bus</option>';

        if (buses.length === 0) {

            busSearch.innerHTML =
                '<option value="">No buses available</option>';

            return;
        }

        buses.forEach(function(bus) {

            const option =
                document.createElement("option");

            option.value = bus.bus_number;

            let statusText = "Available";

            if (
                bus.status === "Active" &&
                bus.trip_direction === "RETURN"
            ) {
                statusText = "Active - Return";

            } else if (
                bus.status === "Active"
            ) {
                statusText = "Active - Outbound";
            }

            option.textContent =
                bus.bus_number +
                " • " +
                statusText +
                " • " +
                (bus.start_location || "Start") +
                " → " +
                (bus.destination || "Destination");

            busSearch.appendChild(option);
        });

    } catch (error) {

        console.error(
            "Bus list error:",
            error
        );

        busSearch.innerHTML =
            '<option value="">Unable to load buses</option>';
    }
}


/* =========================================================
   SHOW / HIDE INDIVIDUAL INFORMATION
========================================================= */

function showBusInformation() {

    const information =
        document.getElementById("busInformation");

    const progress =
        document.getElementById("progressSection");

    const nextStop =
        document.getElementById("nextStopSection");

    const legend =
        document.getElementById("routeLegend");

    if (information) {
        information.classList.add("visible");
    }

    if (progress) {
        progress.style.display = "block";
    }

    if (nextStop) {
        nextStop.style.display = "grid";
    }

    if (legend) {
        legend.style.display = "block";
    }
}


function hideBusInformation() {

    const information =
        document.getElementById("busInformation");

    const progress =
        document.getElementById("progressSection");

    const nextStop =
        document.getElementById("nextStopSection");

    const legend =
        document.getElementById("routeLegend");

    if (information) {
        information.classList.remove("visible");
    }

    if (progress) {
        progress.style.display = "none";
    }

    if (nextStop) {
        nextStop.style.display = "none";
    }

    if (legend) {
        legend.style.display = "none";
    }
}


/* =========================================================
   MESSAGE
========================================================= */

function showMessage(text, type) {

    const message =
        document.getElementById("searchMessage");

    if (!message) {
        return;
    }

    message.textContent = text;

    message.className =
        "search-message " +
        (type || "");
}


/* =========================================================
   ALL BUS MARKERS
========================================================= */

function updateAllBusMarkers(buses) {

    const currentNumbers = new Set();

    buses.forEach(function(bus) {

        if (
            bus.latitude === null ||
            bus.latitude === undefined ||
            bus.longitude === null ||
            bus.longitude === undefined
        ) {
            return;
        }

        const busNumber = bus.bus_number;

        currentNumbers.add(busNumber);

        const position = [
            Number(bus.latitude),
            Number(bus.longitude)
        ];

        if (!allBusMarkers[busNumber]) {

            const marker =
                L.marker(
                    position,
                    {
                        icon: createBusIcon(bus)
                    }
                ).addTo(map);

            marker.bindPopup(
                createBusPopup(bus)
            );

            allBusMarkers[busNumber] = {
                marker: marker,
                position: position
            };

        } else {

            const markerData =
                allBusMarkers[busNumber];

            markerData.marker.setIcon(
                createBusIcon(bus)
            );

            markerData.marker.setLatLng(
                position
            );

            markerData.marker.bindPopup(
                createBusPopup(bus)
            );

            markerData.position = position;
        }
    });


    /* REMOVE BUSES THAT NO LONGER EXIST */

    Object.keys(allBusMarkers).forEach(
        function(busNumber) {

            if (!currentNumbers.has(busNumber)) {

                map.removeLayer(
                    allBusMarkers[busNumber].marker
                );

                delete allBusMarkers[busNumber];
            }
        }
    );
}


/* =========================================================
   ALL BUS POPUP
========================================================= */

function createBusPopup(bus) {

    const direction =
        bus.trip_direction === "RETURN"
            ? "Return"
            : "Outbound";

    const status =
        bus.status === "Active"
            ? "Active"
            : "Available";

    const progress =
        Number(
            bus.progress_percentage || 0
        );

    return (
        "<b>" +
        escapeHtml(bus.bus_number) +
        "</b><br>" +

        "Status: " +
        escapeHtml(status) +
        "<br>" +

        "Direction: " +
        escapeHtml(direction) +
        "<br>" +

        "Route: " +
        escapeHtml(bus.start_location || "") +
        " → " +
        escapeHtml(bus.destination || "") +
        "<br>" +

        "Progress: " +
        Math.round(progress) +
        "%"
    );
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value === null ||
        value === undefined
            ? ""
            : String(value);

    return div.innerHTML;
}


/* =========================================================
   LOAD ALL BUS LOCATIONS
========================================================= */

async function loadAllBuses() {

    try {

        const response =
            await fetch(
                "/api/buses",
                {
                    cache: "no-store"
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Unable to load buses"
            );
        }

        const buses =
            data.buses || [];

        allBusData =
            buses;

        updateAllBusMarkers(
            buses
        );

        updateBusDropdown(
            buses
        );

    } catch (error) {

        console.error(
            "All bus location error:",
            error
        );
    }
}


/* =========================================================
   UPDATE DROPDOWN WITHOUT LOSING SELECTION
========================================================= */

function updateBusDropdown(buses) {

    const busSearch =
        document.getElementById("busSearch");

    if (!busSearch) {
        return;
    }

    const previousValue =
        busSearch.value;

    busSearch.innerHTML =
        '<option value="">Select a bus</option>';

    buses.forEach(function(bus) {

        const option =
            document.createElement("option");

        option.value =
            bus.bus_number;

        let statusText =
            "Available";

        if (bus.status === "Active") {

            statusText =
                bus.trip_direction === "RETURN"
                    ? "Active - Return"
                    : "Active - Outbound";
        }

        option.textContent =
            bus.bus_number +
            " • " +
            statusText +
            " • " +
            (bus.start_location || "Start") +
            " → " +
            (bus.destination || "Destination");

        busSearch.appendChild(option);
    });

    if (
        selectedBus &&
        buses.some(
            bus =>
                bus.bus_number === selectedBus
        )
    ) {

        busSearch.value =
            selectedBus;

    } else {

        busSearch.value =
            previousValue || "";
    }
}


/* =========================================================
   SELECT BUS
========================================================= */

function searchBus() {

    const inputElement =
        document.getElementById("busSearch");

    if (!inputElement) {
        return;
    }

    const input =
        inputElement.value
            .trim()
            .toUpperCase();

    /* NO BUS SELECTED */

    if (input === "") {

        returnToAllBusesMode();

        return;
    }

    /* SELECT BUS */

    selectedBus =
        input;

    if (liveTimer) {

        clearInterval(
            liveTimer
        );

        liveTimer =
            null;
    }

    showBusInformation();

    showMessage(
        "Loading " + input + "...",
        ""
    );

    getLiveBusLocation();

    liveTimer =
        setInterval(
            getLiveBusLocation,
            3000
        );
}


/* =========================================================
   RETURN TO ALL BUS MODE
========================================================= */

function returnToAllBusesMode() {

    selectedBus =
        null;

    if (liveTimer) {

        clearInterval(
            liveTimer
        );

        liveTimer =
            null;
    }

    clearSelectedBusData();

    hideBusInformation();

    const allMessage =
        document.getElementById(
            "allBusesMessage"
        );

    if (allMessage) {

        allMessage.style.display =
            "block";
    }

    showMessage(
        "Showing all buses on the map.",
        "success"
    );

    loadAllBuses();
}


/* =========================================================
   GET SELECTED BUS
========================================================= */

async function getLiveBusLocation() {

    if (!selectedBus) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/bus/" +
                encodeURIComponent(selectedBus),
                {
                    cache: "no-store"
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            showMessage(
                data.message ||
                "Bus not found.",
                "error"
            );

            return;
        }

        updateBusInformation(
            data
        );

        updateRoute(
            data.stops,
            data.bus.trip_direction
        );

        updateStopMarkers(
            data
        );

        updateSelectedBusMarker(
            data
        );

        updateProgress(
            data
        );

        updateNextStop(
            data
        );

        const allMessage =
            document.getElementById(
                "allBusesMessage"
            );

        if (allMessage) {

            allMessage.style.display =
                "none";
        }

        /* Keep all bus positions updated */

        loadAllBuses();

        /* STATUS MESSAGE */

        if (data.bus.destination_reached) {

            showMessage(
                "Destination reached. Bus is available for the next journey.",
                "success"
            );

        } else if (
            data.bus.status === "Active"
        ) {

            if (
                data.bus.trip_direction === "RETURN"
            ) {

                showMessage(
                    "Live tracking active. Bus is returning to " +
                    data.bus.destination +
                    ".",
                    "success"
                );

            } else {

                showMessage(
                    "Live tracking active. Bus is travelling to " +
                    data.bus.destination +
                    ".",
                    "success"
                );
            }

        } else {

            showMessage(
                "Bus is currently available and waiting for the next journey.",
                "success"
            );
        }

    } catch (error) {

        console.error(
            "Live tracking error:",
            error
        );

        showMessage(
            "Unable to connect to live tracking.",
            "error"
        );
    }
}


/* =========================================================
   UPDATE BUS INFORMATION
========================================================= */

function updateBusInformation(data) {

    const bus =
        data.bus;

    const stops =
        data.stops || [];


    /* BUS NUMBER */

    const busNumber =
        document.getElementById("busNumber");

    if (busNumber) {

        busNumber.textContent =
            bus.bus_number;
    }


    /* ROUTE */

    const busRoute =
        document.getElementById("busRoute");

    if (busRoute) {

        busRoute.textContent =
            bus.route_name;
    }


    /* CURRENT LOCATION */

    const currentStop =
        Number(
            bus.current_stop || 1
        );

    const currentStopData =
        stops.find(
            function(stop) {

                return Number(
                    stop.stop_order
                ) === currentStop;
            }
        );

    const busLocation =
        document.getElementById(
            "busLocation"
        );

    if (busLocation) {

        if (currentStopData) {

            busLocation.textContent =
                currentStopData.stop_name;

        } else {

            busLocation.textContent =
                "Location unavailable";
        }
    }


    /* DESTINATION */

    const busDestination =
        document.getElementById(
            "busDestination"
        );

    if (busDestination) {

        busDestination.textContent =
            bus.destination;
    }


    /* ETA */

    const busETA =
        document.getElementById("busETA");

    if (busETA) {

        if (bus.status === "Active") {

            busETA.textContent =
                bus.eta || "Calculating...";

        } else {

            busETA.textContent =
                bus.destination_reached
                    ? "Arrived"
                    : "Ready";
        }
    }


    /* STATUS */

    const statusElement =
        document.getElementById(
            "busStatus"
        );

    if (!statusElement) {
        return;
    }

    if (bus.status === "Active") {

        statusElement.textContent =
            bus.trip_direction === "RETURN"
                ? "Active - Return"
                : "Active";

        statusElement.className =
            "bus-status active";

    } else {

        statusElement.textContent =
            "Available";

        statusElement.className =
            "bus-status available";
    }
}


/* =========================================================
   UPDATE NEXT STOP
========================================================= */

function updateNextStop(data) {

    const nextStop =
        data.next_stop;

    const bus =
        data.bus;

    const nextStopName =
        document.getElementById(
            "nextStopName"
        );

    const nextStopDetails =
        document.getElementById(
            "nextStopDetails"
        );

    const nextStopETA =
        document.getElementById(
            "nextStopETA"
        );

    if (
        !nextStopName ||
        !nextStopDetails ||
        !nextStopETA
    ) {
        return;
    }


    /* DESTINATION */

    if (bus.destination_reached) {

        nextStopName.textContent =
            "Ready for Next Journey";

        nextStopDetails.textContent =
            "Currently at " +
            bus.destination;

        nextStopETA.textContent =
            "Arrived";

        return;
    }


    /* NOT ACTIVE */

    if (bus.status !== "Active") {

        nextStopName.textContent =
            "Ready to Depart";

        nextStopDetails.textContent =
            bus.start_location +
            " → " +
            bus.destination;

        nextStopETA.textContent =
            "--";

        return;
    }


    /* NO NEXT STOP */

    if (!nextStop) {

        nextStopName.textContent =
            "Destination";

        nextStopDetails.textContent =
            bus.destination;

        nextStopETA.textContent =
            bus.eta || "--";

        return;
    }


    /* NEXT STOP */

    nextStopName.textContent =
        nextStop.stop_name;

    if (
        bus.trip_direction === "RETURN"
    ) {

        nextStopDetails.textContent =
            "Returning to " +
            bus.destination;

    } else {

        nextStopDetails.textContent =
            "Travelling to " +
            bus.destination;
    }

    nextStopETA.textContent =
        bus.eta || "--";
}


/* =========================================================
   UPDATE PROGRESS
========================================================= */

function updateProgress(data) {

    const bus =
        data.bus;

    let percentage =
        Number(
            bus.progress_percentage
        );

    if (Number.isNaN(percentage)) {
        percentage = 0;
    }

    percentage =
        Math.max(
            0,
            Math.min(
                100,
                percentage
            )
        );

    percentage =
        Math.round(percentage);


    /* BAR */

    const progressBar =
        document.getElementById(
            "progressBar"
        );

    if (progressBar) {

        progressBar.style.width =
            percentage + "%";
    }


    /* PERCENTAGE */

    const progressPercentage =
        document.getElementById(
            "progressPercentage"
        );

    if (progressPercentage) {

        progressPercentage.textContent =
            percentage + "%";
    }


    /* START */

    const progressStart =
        document.getElementById(
            "progressStart"
        );

    if (progressStart) {

        progressStart.textContent =
            bus.start_location;
    }


    /* END */

    const progressEnd =
        document.getElementById(
            "progressEnd"
        );

    if (progressEnd) {

        progressEnd.textContent =
            bus.destination;
    }


    /* CURRENT STOP */

    const progressStop =
        document.getElementById(
            "progressStop"
        );

    if (progressStop) {

        progressStop.textContent =
            "Stop " +
            bus.current_stop +
            " / " +
            bus.total_stops;
    }
}


/* =========================================================
   UPDATE ROUTE
========================================================= */

function updateRoute(stops, direction) {

    if (
        !stops ||
        stops.length < 2
    ) {
        return;
    }

    let routeStops =
        [...stops];

    if (direction === "RETURN") {
        routeStops.reverse();
    }

    const coordinates =
        routeStops.map(
            function(stop) {

                return [
                    Number(stop.latitude),
                    Number(stop.longitude)
                ];
            }
        );

    if (routeLine) {

        routeLine.setLatLngs(
            coordinates
        );

    } else {

        routeLine =
            L.polyline(
                coordinates,
                {
                    color: "#2563eb",
                    weight: 5,
                    opacity: 0.8
                }
            ).addTo(map);
    }
}


/* =========================================================
   UPDATE STOP MARKERS
========================================================= */

function updateStopMarkers(data) {

    const stops =
        data.stops || [];

    const bus =
        data.bus;

    const currentStop =
        Number(
            bus.current_stop || 1
        );

    const direction =
        bus.trip_direction ||
        "OUTBOUND";


    stopMarkers.forEach(
        function(marker) {

            map.removeLayer(marker);
        }
    );

    stopMarkers = [];

    if (stops.length === 0) {
        return;
    }


    let startOrder;
    let destinationOrder;

    if (direction === "RETURN") {

        startOrder =
            stops.length;

        destinationOrder =
            1;

    } else {

        startOrder =
            1;

        destinationOrder =
            stops.length;
    }


    stops.forEach(
        function(stop) {

            const order =
                Number(stop.stop_order);

            let type =
                "upcoming";


            /* REACHED */

            if (direction === "OUTBOUND") {

                if (order < currentStop) {
                    type = "reached";
                }

            } else {

                if (order > currentStop) {
                    type = "reached";
                }
            }


            /* CURRENT */

            if (
                order === currentStop &&
                !bus.destination_reached
            ) {
                type = "next";
            }


            /* DESTINATION */

            if (
                order === destinationOrder &&
                bus.destination_reached
            ) {
                type = "destination";
            }


            /* START */

            if (
                order === startOrder &&
                bus.status !== "Active" &&
                !bus.destination_reached
            ) {
                type = "start";
            }


            const marker =
                L.marker(
                    [
                        Number(stop.latitude),
                        Number(stop.longitude)
                    ],
                    {
                        icon:
                            createStopIcon(type)
                    }
                ).addTo(map);


            let label =
                "Upcoming stop";

            if (type === "reached") {
                label = "Reached";
            }

            if (type === "next") {
                label = "Current stop";
            }

            if (type === "destination") {
                label = "Destination";
            }

            if (type === "start") {
                label = "Starting point";
            }


            marker.bindPopup(
                "<b>" +
                escapeHtml(stop.stop_name) +
                "</b><br>" +

                label +
                "<br>" +

                "Stop " +
                stop.stop_order +
                " / " +
                stops.length
            );

            stopMarkers.push(marker);
        }
    );
}


/* =========================================================
   UPDATE SELECTED BUS MARKER
========================================================= */

function updateSelectedBusMarker(data) {

    const bus =
        data.bus;

    if (
        bus.latitude === null ||
        bus.latitude === undefined ||
        bus.longitude === null ||
        bus.longitude === undefined
    ) {
        return;
    }

    const newPosition = [
        Number(bus.latitude),
        Number(bus.longitude)
    ];


    /* CREATE */

    if (!currentMarker) {

        currentMarker =
            L.marker(
                newPosition,
                {
                    icon:
                        createBusIcon(bus)
                }
            ).addTo(map);

        lastPosition =
            newPosition;

        map.panTo(
            newPosition
        );

    } else {

        currentMarker.setIcon(
            createBusIcon(bus)
        );

        animateBusMarker(
            lastPosition ||
            currentMarker.getLatLng(),
            newPosition
        );
    }


    const directionText =
        bus.trip_direction === "RETURN"
            ? "Return"
            : "Outbound";

    currentMarker.bindPopup(
        "<b>" +
        escapeHtml(bus.bus_number) +
        "</b><br>" +

        "Status: " +
        escapeHtml(bus.status) +
        "<br>" +

        "Direction: " +
        directionText +
        "<br>" +

        "Stop: " +
        bus.current_stop +
        " / " +
        bus.total_stops +
        "<br>" +

        "Progress: " +
        Math.round(
            Number(
                bus.progress_percentage || 0
            )
        ) +
        "%"
    );
}


/* =========================================================
   ANIMATE SELECTED BUS
========================================================= */

function animateBusMarker(start, end) {

    if (!currentMarker) {
        return;
    }


    if (
        start &&
        start.lat !== undefined
    ) {

        start = [
            start.lat,
            start.lng
        ];
    }


    if (
        !Array.isArray(start) ||
        start.length < 2
    ) {

        start = end;
    }


    if (animationFrame) {

        cancelAnimationFrame(
            animationFrame
        );
    }


    const duration = 2600;

    const startTime =
        performance.now();


    function animate(currentTime) {

        const elapsed =
            currentTime -
            startTime;

        const animationProgress =
            Math.min(
                elapsed / duration,
                1
            );

        const eased =
            animationProgress *
            (
                2 -
                animationProgress
            );


        const latitude =
            start[0] +
            (
                end[0] -
                start[0]
            ) *
            eased;


        const longitude =
            start[1] +
            (
                end[1] -
                start[1]
            ) *
            eased;


        currentMarker.setLatLng(
            [
                latitude,
                longitude
            ]
        );


        if (
            animationProgress < 1
        ) {

            animationFrame =
                requestAnimationFrame(
                    animate
                );

        } else {

            lastPosition =
                end;

            animationFrame =
                null;
        }
    }


    animationFrame =
        requestAnimationFrame(
            animate
        );
}


/* =========================================================
   CLEAR SELECTED BUS DATA
========================================================= */

function clearSelectedBusData() {

    /* SELECTED MARKER */

    if (currentMarker) {

        map.removeLayer(
            currentMarker
        );

        currentMarker =
            null;
    }


    /* ROUTE */

    if (routeLine) {

        map.removeLayer(
            routeLine
        );

        routeLine =
            null;
    }


    /* STOP MARKERS */

    stopMarkers.forEach(
        function(marker) {

            map.removeLayer(
                marker
            );
        }
    );

    stopMarkers = [];


    /* POSITION */

    lastPosition =
        null;


    /* ANIMATION */

    if (animationFrame) {

        cancelAnimationFrame(
            animationFrame
        );

        animationFrame =
            null;
    }
}


/* =========================================================
   BUS DROPDOWN
========================================================= */

function setupBusDropdown() {

    const busSearch =
        document.getElementById(
            "busSearch"
        );

    if (!busSearch) {
        return;
    }


    busSearch.addEventListener(
        "change",
        function() {

            if (this.value) {

                searchBus();

            } else {

                returnToAllBusesMode();
            }
        }
    );


    busSearch.addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter"
            ) {

                searchBus();
            }
        }
    );
}


/* =========================================================
   INITIAL PAGE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        hideBusInformation();

        showMessage(
            "Showing all buses on the map.",
            "success"
        );

        setupBusDropdown();

        loadBusList();

        loadAllBuses();

        allBusesTimer =
            setInterval(
                loadAllBuses,
                3000
            );
    }
);

// script.js - Dynamic slot management, visual selection, and AJAX booking

let currentSelectedSlot = "";
const isFileProtocol = window.location.protocol === "file:";

// Local demo state for when the file is opened directly via file:/// without a web server
let localSlots = [
    { slot_number: "A1", status: "Available" },
    { slot_number: "A2", status: "Available" },
    { slot_number: "A3", status: "Occupied" },
    { slot_number: "A4", status: "Available" },
    { slot_number: "B1", status: "Available" },
    { slot_number: "B2", status: "Occupied" },
    { slot_number: "B3", status: "Available" },
    { slot_number: "B4", status: "Available" }
];
let localBookings = [
    { id: 1, slot_number: "A3", vehicle_number: "KA 01 AB 1234", customer_name: "Demo User", entry_time: "2026-09-18 20:30:00" },
    { id: 2, slot_number: "B2", vehicle_number: "MH 02 CD 5678", customer_name: "Demo User 2", entry_time: "2026-09-18 20:45:00" }
];

document.addEventListener("DOMContentLoaded", () => {
    // Show a helpful warning banner if opened via file:/// protocol
    if (isFileProtocol) {
        showServerNotice();
    }

    // Initial fetch of slot statuses from database
    loadSlots();

    // Attach form submission handler
    const bookingForm = document.getElementById("bookingForm");
    if (bookingForm) {
        bookingForm.addEventListener("submit", handleBookingSubmit);
    }

    // Auto-refresh slot statuses every 15 seconds if running on a web server
    if (!isFileProtocol) {
        setInterval(loadSlots, 15000);
    }
});

/**
 * Displays an informational banner when opened directly via file://
 */
function showServerNotice() {
    let notice = document.getElementById("serverNotice");
    if (!notice) {
        notice = document.createElement("div");
        notice.id = "serverNotice";
        notice.style.cssText = `
            background: #fffbeb;
            color: #92400e;
            padding: 14px 20px;
            border-bottom: 2px solid #fde68a;
            text-align: center;
            font-size: 0.92rem;
            line-height: 1.5;
            position: sticky;
            top: 0;
            z-index: 1000;
        `;
        notice.innerHTML = `
            <strong>⚠️ Running via File Protocol (<code>file:///</code>)</strong>: 
            Database operations require the Python Flask backend. 
            <br>
            To connect with your database, start the backend with <code>python app.py</code> and open 
            <strong><a href="http://127.0.0.1:5000" target="_blank">http://127.0.0.1:5000</a></strong>.
            <em>(A simulated local demo is currently active below).</em>
        `;
        document.body.prepend(notice);
    }
}

/**
 * Fetches latest slots and active bookings from the database via /api/slots
 */
async function loadSlots() {
    if (isFileProtocol) {
        renderLocalData();
        return;
    }

    try {
        const response = await fetch("/api/slots");
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.success) {
            renderSlots(data.slots);
            updateStats(data.stats);
            renderActiveBookings(data.active_bookings);
        } else {
            console.error("Failed to load slots:", data.message);
        }
    } catch (err) {
        console.warn("Could not fetch live slots from /api/slots. Falling back to local state.", err);
        renderLocalData();
    }
}

/**
 * Renders fallback data when opened offline or via file://
 */
function renderLocalData() {
    const stats = {
        total: localSlots.length,
        available: localSlots.filter(s => s.status.toLowerCase() === "available").length,
        occupied: localSlots.filter(s => s.status.toLowerCase() !== "available").length
    };
    renderSlots(localSlots);
    updateStats(stats);
    renderActiveBookings(localBookings);
}

/**
 * Dynamically renders slot buttons based on current state
 */
function renderSlots(slots) {
    const slotsContainer = document.getElementById("slotsContainer");
    if (!slotsContainer) return;

    slotsContainer.innerHTML = "";

    slots.forEach(slot => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = `slot-${slot.slot_number}`;
        const isAvailable = (slot.status || "").toLowerCase() === "available";
        const isSelected = slot.slot_number === currentSelectedSlot;

        btn.className = `slot ${isAvailable ? "available" : "occupied"} ${isSelected ? "selected" : ""}`;
        
        btn.innerHTML = `
            <span>${slot.slot_number}</span>
            <small>${isAvailable ? "Available" : "Occupied"}</small>
        `;

        if (isAvailable) {
            btn.onclick = () => selectSlot(slot.slot_number);
        } else {
            btn.disabled = true;
            btn.title = `Slot ${slot.slot_number} is currently occupied`;
        }

        slotsContainer.appendChild(btn);
    });
}

/**
 * Updates slot counter badges
 */
function updateStats(stats) {
    if (!stats) return;
    const elTotal = document.getElementById("statTotal");
    const elAvailable = document.getElementById("statAvailable");
    const elOccupied = document.getElementById("statOccupied");

    if (elTotal) elTotal.textContent = stats.total ?? 0;
    if (elAvailable) elAvailable.textContent = stats.available ?? 0;
    if (elOccupied) elOccupied.textContent = stats.occupied ?? 0;
}

/**
 * Handles slot selection with visual highlight
 */
function selectSlot(slot) {
    currentSelectedSlot = slot;

    // Update input field
    const input = document.getElementById("selectedSlot");
    if (input) {
        input.value = slot;
    }

    // Update visual active state across all slot buttons
    document.querySelectorAll(".slots .slot").forEach(btn => {
        btn.classList.remove("selected");
    });

    const activeBtn = document.getElementById(`slot-${slot}`);
    if (activeBtn) {
        activeBtn.classList.add("selected");
    }

    showToast(`Slot ${slot} selected. Complete details to reserve.`, "success");
}

/**
 * Submits the reservation asynchronously via AJAX
 */
async function handleBookingSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector("button[type='submit']");
    const originalText = submitBtn.innerHTML;

    const formData = new FormData(form);
    const slotNumber = formData.get("slot_number");
    const customerName = formData.get("customer_name");
    const vehicleNumber = formData.get("vehicle_number");

    // Client-side validation
    if (!slotNumber) {
        showToast("Please click on an available slot first!", "error");
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = "Reserving...";

    // If opened via file://, simulate reservation locally so user can test the UI
    if (isFileProtocol) {
        setTimeout(() => {
            const slotObj = localSlots.find(s => s.slot_number === slotNumber);
            if (slotObj) slotObj.status = "Occupied";
            localBookings.unshift({
                id: Date.now(),
                slot_number: slotNumber,
                vehicle_number: vehicleNumber,
                customer_name: customerName,
                entry_time: new Date().toLocaleTimeString()
            });

            showToast(`[Demo Mode] Slot ${slotNumber} reserved for ${vehicleNumber}.`, "success");
            form.reset();
            currentSelectedSlot = "";
            const slotInput = document.getElementById("selectedSlot");
            if (slotInput) slotInput.value = "";
            renderLocalData();

            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }, 500);
        return;
    }

    formData.append("ajax", "1");

    try {
        const response = await fetch("/api/reserve", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Success! Slot ${result.slot_number} reserved for ${result.vehicle_number}.`, "success");
            form.reset();
            currentSelectedSlot = "";
            const slotInput = document.getElementById("selectedSlot");
            if (slotInput) slotInput.value = "";
            await loadSlots();
        } else {
            showToast(result.message || "Reservation failed.", "error");
        }
    } catch (err) {
        console.error("Booking error:", err);
        showToast("Could not contact server. Please ensure Apache and MySQL are running.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

/**
 * Renders active reservations in the checkout panel
 */
function renderActiveBookings(bookings) {
    const tableBody = document.getElementById("activeBookingsBody");
    const emptyMsg = document.getElementById("noBookingsMsg");
    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (!bookings || bookings.length === 0) {
        if (emptyMsg) emptyMsg.style.display = "block";
        return;
    }

    if (emptyMsg) emptyMsg.style.display = "none";

    bookings.forEach(b => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong class="badge-slot">${b.slot_number}</strong></td>
            <td>${escapeHtml(b.vehicle_number)}</td>
            <td>${escapeHtml(b.customer_name)}</td>
            <td>${b.entry_time}</td>
            <td>
                <button class="btn-release" onclick="releaseVehicle('${b.slot_number}', ${b.id})">
                    Check Out
                </button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

/**
 * Check out an active vehicle and mark the slot Available again
 */
async function releaseVehicle(slotNumber, bookingId) {
    if (!confirm(`Are you sure you want to check out vehicle in slot ${slotNumber}?`)) {
        return;
    }

    if (isFileProtocol) {
        const slotObj = localSlots.find(s => s.slot_number === slotNumber);
        if (slotObj) slotObj.status = "Available";
        localBookings = localBookings.filter(b => b.id != bookingId);
        showToast(`[Demo Mode] Slot ${slotNumber} released!`, "success");
        renderLocalData();
        return;
    }

    const formData = new FormData();
    formData.append("slot_number", slotNumber);
    formData.append("booking_id", bookingId);
    formData.append("ajax", "1");

    try {
        const response = await fetch("/api/release", {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const res = await response.json();

        if (res.success) {
            showToast(`Slot ${res.slot_number} released! Fee: $${res.amount}`, "success");
            await loadSlots();
        } else {
            showToast(res.message || "Could not check out vehicle.", "error");
        }
    } catch (err) {
        console.error("Checkout error:", err);
        showToast("Error processing checkout.", "error");
    }
}

/**
 * Helper to show toast notification
 */
function showToast(message, type = "success") {
    let toast = document.getElementById("toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "toast";
        document.body.appendChild(toast);
    }

    toast.className = type;
    toast.textContent = message;
    toast.style.display = "block";

    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
        toast.style.display = "none";
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, match => {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return map[match];
    });
}

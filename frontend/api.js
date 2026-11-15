
const API_BASE = "http://127.0.0.1:8000";

// ---------- Authentication storage ----------

function saveToken(token) {
    sessionStorage.setItem("grit_token", token);
}

function getToken() {
    return sessionStorage.getItem("grit_token");
}

function getUser() {
    const user = sessionStorage.getItem("grit_user");
    return user ? JSON.parse(user) : null;
}

function clearAuthSession() {
    sessionStorage.removeItem("grit_token");
    sessionStorage.removeItem("grit_user");
}

function logout() {
    clearAuthSession();
    window.location.href = "login.html";
}

// ---------- Role-based navigation ----------

function getRoleDashboard(user) {
    if (!user || !user.role) {
        return "login.html";
    }

    switch (user.role.toLowerCase()) {
        case "student":
            return "student.html";

        case "interviewer":
            return "interviewer.html";

        case "admin":
            return "admin.html";

        default:
            return "login.html";
    }
}

// ---------- API request helper ----------

async function apiRequest(endpoint, options = {}) {
    const token = getToken();

    const response = await fetch(API_BASE + endpoint, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(token ? {
                "Authorization": "Bearer " + token
            } : {}),
            ...(options.headers || {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        if (response.status === 401) {
            clearAuthSession();
        }

        throw new Error(
            data.detail || "Unable to complete request"
        );
    }

    return data;
}

// ---------- Login ----------

async function login(email, password) {
    const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
            email: email,
            password: password
        })
    });

    saveToken(data.access_token);

    sessionStorage.setItem(
        "grit_user",
        JSON.stringify(data.user)
    );

    return data.user;
}

// ---------- Profile ----------

async function getProfile() {
    return await apiRequest("/auth/me");
}

// ---------- Bookings ----------

async function getMyBookings() {
    return await apiRequest("/me/bookings");
}

async function getBookings() {
    return await apiRequest("/bookings");
}

async function bookInterview(slotId) {
    return await apiRequest("/bookings", {
        method: "POST",
        body: JSON.stringify({
            slot_id: slotId
        })
    });
}

async function cancelInterview(bookingId) {
    return await apiRequest(
        "/bookings/" + encodeURIComponent(bookingId) + "/cancel",
        {
            method: "POST"
        }
    );
}

// ---------- Interview slots ----------

async function getAvailableSlots() {
    return await apiRequest("/slots");
}

async function getStudentAvailableSlots() {
    return await apiRequest("/student/available-slots");
}

// ---------- Interview results ----------

async function recordInterviewResult(bookingId, result, feedback) {
    return await apiRequest(
        "/bookings/" + encodeURIComponent(bookingId) + "/result",
        {
            method: "POST",
            body: JSON.stringify({
                result: result,
                feedback: feedback
            })
        }
    );
}

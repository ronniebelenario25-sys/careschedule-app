import sqlite3
import datetime
import streamlit as st

# ==========================================
# 1. DATABASE MANAGEMENT
# ==========================================
class DatabaseManager:
    """Handles SQLite database creation and connections."""
    def __init__(self, db_name="careschedule_v2.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create Patients Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    contact TEXT NOT NULL
                )
            """)

            # Create Appointments Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    doctor_name TEXT NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Scheduled',
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            """)
            conn.commit()

# Initialize DB Instance
db = DatabaseManager()

# ==========================================
# 2. OBJECT-ORIENTED PROGRAMMING (OOP Classes)
# ==========================================
class Patient:
    """Encapsulates Patient details and database CRUD operations."""
    def __init__(self, full_name, age, gender, contact, patient_id=None):
        self.patient_id = patient_id
        self.full_name = full_name
        self.age = age
        self.gender = gender
        self.contact = contact

    def save_to_db(self):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO patients (full_name, age, gender, contact)
                VALUES (?, ?, ?, ?)
            """, (self.full_name, self.age, self.gender, self.contact))
            conn.commit()

    @staticmethod
    def get_all_patients():
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patients")
            return cursor.fetchall()


class Appointment:
    """Handles scheduling logic and double-booking validation."""
    def __init__(self, patient_id, doctor_name, date_str, time_str, status="Scheduled"):
        self.patient_id = patient_id
        self.doctor_name = doctor_name
        self.date_str = date_str
        self.time_str = time_str
        self.status = status

    def is_slot_available(self):
        """Checks for double-booking conflicts."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE doctor_name = ? AND appointment_date = ? AND appointment_time = ? AND status != 'Canceled'
            """, (self.doctor_name, self.date_str, self.time_str))
            existing = cursor.fetchone()
            return existing is None

    def book(self):
        if not self.is_slot_available():
            return False, "This time slot is already booked for the selected doctor!"

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO appointments (patient_id, doctor_name, appointment_date, appointment_time, status)
                VALUES (?, ?, ?, ?, ?)
            """, (self.patient_id, self.doctor_name, self.date_str, self.time_str, self.status))
            conn.commit()
        return True, "Appointment successfully booked!"

    @staticmethod
    def update_status(appointment_id, new_status):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE appointments SET status = ? WHERE appointment_id = ?
            """, (new_status, appointment_id))
            conn.commit()

    @staticmethod
    def get_appointments_with_details():
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.appointment_id, p.full_name, a.doctor_name, a.appointment_date, a.appointment_time, a.status
                FROM appointments a
                JOIN patients p ON a.patient_id = p.patient_id
                ORDER BY a.appointment_date, a.appointment_time
            """)
            return cursor.fetchall()

# ==========================================
# 3. AUTHENTICATION & LOGIN SYSTEM
# ==========================================
st.set_page_config(page_title="CareSchedule - Clinic Manager", page_icon="🏥", layout="wide")

# Predefined User Accounts (Demonstration Purposes)
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "patient": {"password": "user123", "role": "Patient"}
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

def login():
    st.title("🏥 CareSchedule - System Login")
    st.write("Please sign in to access the system.")
    
    with st.form("login_form"):
        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password").strip()
        submit = st.form_submit_button("Sign In")
        
        if submit:
            if username in USERS and USERS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = USERS[username]["role"]
                st.session_state.username = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    st.info("**Demo Accounts:**\n* **Admin:** Username `admin` | Password `admin123`\n* **Patient:** Username `patient` | Password `user123`")

def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

# Execute Login Prompt if Not Authenticated
if not st.session_state.logged_in:
    login()
    st.stop()

# ==========================================
# 4. STREAMLIT WEB INTERFACE & PERMISSIONS
# ==========================================
st.sidebar.title(f"Welcome, {st.session_state.username.capitalize()}!")
st.sidebar.caption(f"Role: **{st.session_state.role}**")
if st.sidebar.button("Logout"):
    logout()

# Role-Based Navigation
if st.session_state.role == "Admin":
    menu = ["Dashboard", "Patient Registration", "Book Appointment", "Manage Appointments"]
else:
    # Patients only have access to registration and booking
    menu = ["Patient Registration", "Book Appointment"]

choice = st.sidebar.selectbox("Navigation Menu", menu)

# --- MODULE 1: DASHBOARD (Admin Only) ---
if choice == "Dashboard":
    st.subheader("📊 System Overview")
    
    patients = Patient.get_all_patients()
    appointments = Appointment.get_appointments_with_details()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Patients", len(patients))
    col2.metric("Total Appointments", len(appointments))
    active_count = sum(1 for a in appointments if a[5] == "Scheduled")
    col3.metric("Upcoming Scheduled", active_count)
    
    st.markdown("---")
    st.subheader("📅 Scheduled Appointments List")
    if appointments:
        st.dataframe(
            appointments, 
            column_config={
                "0": "ID", "1": "Patient Name", "2": "Doctor", 
                "3": "Date", "4": "Time", "5": "Status"
            },
            use_container_width=True
        )
    else:
        st.info("No appointments currently found in the system.")

# --- MODULE 2: PATIENT REGISTRATION ---
elif choice == "Patient Registration":
    st.subheader("👤 Register Patient")
    
    with st.form("patient_form"):
        name = st.text_input("Full Name")
        col1, col2 = st.columns(2)
        age = col1.number_input("Age", min_value=1, max_value=120, value=25)
        gender = col2.selectbox("Gender", ["Male", "Female", "Other"])
        contact = st.text_input("Contact Number")
        
        submit = st.form_submit_button("Register Patient")
        
        if submit:
            if not name.strip() or not contact.strip():
                st.error("Please fill out all required fields.")
            else:
                new_patient = Patient(name, age, gender, contact)
                new_patient.save_to_db()
                st.success(f"Patient '{name}' successfully registered!")

    if st.session_state.role == "Admin":
        st.markdown("---")
        st.subheader("Registered Patients Directory")
        patient_list = Patient.get_all_patients()
        if patient_list:
            st.dataframe(patient_list, use_container_width=True)

# --- MODULE 3: BOOK APPOINTMENT ---
elif choice == "Book Appointment":
    st.subheader("📅 Schedule New Appointment")
    
    patient_list = Patient.get_all_patients()
    
    if not patient_list:
        st.warning("No registered patients found. Please register a patient profile first.")
    else:
        patient_options = {f"{p[1]} (ID: {p[0]})": p[0] for p in patient_list}
        selected_patient = st.selectbox("Select Patient Profile", list(patient_options.keys()))
        patient_id = patient_options[selected_patient]
        
        doctor_name = st.selectbox("Select Doctor", ["Dr. Smith (General Medicine)", "Dr. Santos (Pediatrics)", "Dr. Reyes (Dentistry)"])
        app_date = st.date_input("Date", min_value=datetime.date.today())
        app_time = st.selectbox("Time Slot", ["09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"])
        
        if st.button("Confirm Booking"):
            new_app = Appointment(patient_id, doctor_name, str(app_date), app_time)
            success, message = new_app.book()
            
            if success:
                st.success(message)
            else:
                st.error(message)

# --- MODULE 4: MANAGE APPOINTMENTS (Admin Only) ---
elif choice == "Manage Appointments":
    st.subheader("⚙️ Update Appointment Status")
    
    appointments = Appointment.get_appointments_with_details()
    
    if not appointments:
        st.info("No appointments available to manage.")
    else:
        app_dict = {f"ID: {a[0]} | {a[1]} with {a[2]} on {a[3]} ({a[4]}) - Status: {a[5]}": a[0] for a in appointments}
        selected_app_label = st.selectbox("Choose Appointment", list(app_dict.keys()))
        selected_id = app_dict[selected_app_label]
        
        new_status = st.selectbox("Update Status To", ["Scheduled", "Completed", "Canceled"])
        
        if st.button("Update Status"):
            Appointment.update_status(selected_id, new_status)
            st.success(f"Appointment ID {selected_id} updated to '{new_status}'!")
            st.rerun()

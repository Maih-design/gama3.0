# Project Overview: Gama Knife Committee Management System (Gama 3.0)

## 1. Project Purpose

The **Gama Knife Committee Management System** (*نظام إدارة اللجنة العليا للجاما نايف*) is an internal clinical-administrative web application built with Django for the Egyptian Health Insurance Organization (*الهيئة العامة للتأمين الصحي*).

The primary purpose of the system is to digitize and manage the operational lifecycle of specialized medical committee sessions—specifically the Higher Gamma Knife Committee, with architectural groundwork laid for the Bone Marrow Transplant Committee (*لجنة زرع النخاع*).

### Key Objectives
* Registering and managing patient profiles under Egyptian Health Insurance laws and regional branch affiliations.
* Organizing and scheduling periodic committee sessions overseen by consultant physicians.
* Enrolling patient cases into active committee sessions.
* Recording clinical recommendations, designated procedures, and session counts.
* Managing referral letters to contracted treatment centers for procedures requiring external intervention.
* Producing standardized, print-ready official documents (committee rosters, decision memos, and referral letters).

---

## 2. Django Applications and Responsibilities

The project comprises two applications alongside the core configuration package:

### 2.1 `config` (Project Configuration)
* Located at `config/`.
* Contains standard Django project configurations:
  * `settings.py`: Defines installed applications, authentication redirects, SQLite database routing, and templates configuration.
  * `urls.py`: Root URL routing, mounting `committee.urls` at `/`, Django admin at `/admin/`, and reserving `/bmt` for `bmt_committee.urls`.
  * `wsgi.py` / `asgi.py`: Web server deployment gateways.

### 2.2 `committee` (Operational Core)
* Located at `committee/`.
* The fully implemented operational application driving the Gamma Knife Committee workflow.
* **Responsibilities**:
  * Patient registry and search indexing.
  * Scheduling and tracking committee session states (`PREPARING` vs. `COMPLETED`).
  * Enrolling cases into sessions and enforcing single-enrollment integrity.
  * Capturing committee recommendations, procedure selections, and session limits.
  * Issuing, updating, and canceling patient referral letters to authorized external centers.
  * Rendering print-optimized HTML templates matching Egyptian administrative stationery.

### 2.3 `bmt_committee` (Extension Stub)
* Located at `bmt_committee/`.
* An initialized application skeleton designated for the Bone Marrow Transplant Committee (*لجنة زرع النخاع*).
* Registered in `config/settings.py` (`INSTALLED_APPS`) and mounted in `config/urls.py`.
* Currently contains standard boilerplate files (`models.py`, `views.py`, `admin.py`, `apps.py`) awaiting domain-specific model and view implementations.

---

## 3. Models and Field Specifications

All domain models are defined in `committee/models.py`. Standard enumerations and choices are maintained in `committee/constants.py`.

### 3.1 `Patient`
Represents an individual patient registered within the health insurance system.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `national_id` | `CharField` | `max_length=14`, `unique=True` | 14-digit Egyptian National ID |
| `full_name` | `CharField` | `max_length=200` | Full name of the patient |
| `gender` | `CharField` | `max_length=10`, `choices=Gender.choices` | `M` (ذكر) or `F` (أنثى) |
| `insurance_law` | `CharField` | `max_length=10`, `choices=InsuranceLaw.choices` | Insurance law (`RET`: معاش ق79, `STD`: طلبة, `CID`: مواليد ق99, `EMP`: موظف ق79) |
| `insurance_number` | `CharField` | `max_length=20` | Health insurance identification number |
| `phone_number` | `CharField` | `max_length=20`, `blank=True` | Contact telephone number |
| `affiliated_branch`| `CharField` | `max_length=100`, `choices=Branches.choices` | Regional insurance branch (21 governorate branches) |
| `diagnosis` | `TextField` | Mandatory | Primary clinical diagnosis text |

### 3.2 `Doctor`
Represents the consultant physician presiding over a committee session.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `full_name` | `CharField` | `max_length=200` | Full name and title of the consultant doctor |

### 3.3 `Procedure`
Defines medical treatments and surgical interventions evaluated by the committee.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `name` | `CharField` | `max_length=200` | Medical procedure name |
| `requires_referral`| `BooleanField` | `default=False` | Whether the procedure requires an external referral letter |
| `category` | `CharField` | `max_length=100` | Classification/specialty category of the procedure |
| `price` | `DecimalField` | `max_digits=10`, `decimal_places=0`, `null=True`, `blank=True` | Monetary cost of the procedure |
| `price_in_words` | `CharField` | `max_length=500`, `blank=True` | Price spelled out in Arabic text for official financial documentation |

### 3.4 `CommitteeSession`
Represents an official assembly date of the medical committee.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `session_date` | `DateField` | Unique per calendar date | Date on which the session is convened |
| `doctor` | `ForeignKey(Doctor)`| `on_delete=models.PROTECT` | Consultant physician presiding over the session |
| `status` | `CharField` | `max_length=20`, `choices=SessionStatus.choices`, `default=PREPARING` | State: `PREPARING` (قيد التجهيز) or `COMPLETED` (مكتملة) |

* **Constraints**: `UniqueConstraint(fields=["session_date"], name="unique_session_per_day")`.

### 3.5 `CommitteeCase`
Represents the enrollment of a specific patient into a specific committee session.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `committee_session`| `ForeignKey(CommitteeSession)` | `on_delete=models.CASCADE`, `related_name="cases"` | The parent session |
| `patient` | `ForeignKey(Patient)` | `on_delete=models.PROTECT`, `related_name="committee_cases"` | Enrolled patient |
| `status` | `CharField` | `max_length=20`, `choices=CaseStatus.choices`, `default=PENDING` | Case status: `PENDING` (قيد المراجعة) or `APPROVED` (معتمد) |

* **Constraints**: `UniqueConstraint(fields=["committee_session", "patient"], name="unique_patient_per_session")`.

### 3.6 `CommitteeRecommendation`
Captures the formal clinical recommendation decided by the committee for an enrolled case.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `committee_case` | `OneToOneField(CommitteeCase)` | `on_delete=models.CASCADE`, `related_name="recommendation"` | The evaluated case (1:1) |
| `procedure` | `ForeignKey(Procedure)` | `on_delete=models.PROTECT`, `related_name="recommendations"` | Selected medical intervention |
| `no_of_sessions` | `PositiveIntegerField` | `validators=[MaxValueValidator(10)]`, `null=True`, `blank=True` | Recommended session count (maximum 10) |
| `recommendation_text` | `TextField` | `blank=True` | Detailed medical directives and notes |
| `created_at` | `DateTimeField` | `auto_now_add=True` | Timestamp of decision entry |

### 3.7 `ReferralCenter`
Authorized external treatment centers and partner hospitals.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `name` | `CharField` | `max_length=200`, `unique=True` | Center name |
| `for_gamma` | `BooleanField` | `default=True` | Authorized for Gamma Knife Committee |
| `for_bone_marrow` | `BooleanField` | `default=False` | Authorized for Bone Marrow Committee |

### 3.8 `Referral`
An official referral letter directing a patient to a contracted center.

| Field | Type | Attributes / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `committee_case` | `ForeignKey(CommitteeCase)` | `on_delete=models.CASCADE`, `related_name="referrals"` | Originating case |
| `referral_center` | `ForeignKey(ReferralCenter)` | `on_delete=models.PROTECT`, `related_name="referrals"` | Destination medical center |
| `status` | `CharField` | `max_length=20`, `choices=ReferralStatus.choices`, `default=ISSUED` | Lifecycle status: `ISSUED` (صادر) or `CANCELLED` (ملغي) |
| `issued_at` | `DateTimeField` | `auto_now_add=True` | Issuance timestamp |
| `cancellation_reason` | `TextField` | `blank=True` | Mandatory explanation when a referral is cancelled |

---

## 4. Entity Relationships

```
Doctor (1) ──────< (N) CommitteeSession (1) ──────< (N) CommitteeCase (N) >────── (1) Patient
                                                             │
                              ┌──────────────────────────────┴──────────────────────────────┐
                              │ (1:1)                                                       │ (1:N)
                              ▼                                                             ▼
                   CommitteeRecommendation (N)                                           Referral (N)
                              │                                                             │
                              │ (N:1)                                                       │ (N:1)
                              ▼                                                             ▼
                          Procedure (1)                                             ReferralCenter (1)
```

### Cardinality Summary
* **`Doctor` → `CommitteeSession`**: One-to-Many (`Doctor` is protected from deletion if sessions reference it).
* **`CommitteeSession` → `CommitteeCase`**: One-to-Many (deleting a session cascades to its enrolled cases).
* **`Patient` → `CommitteeCase`**: One-to-Many (`Patient` is protected from deletion if linked to cases).
* **`CommitteeCase` ↔ `CommitteeRecommendation`**: One-to-One (each case can have at most one official decision; cascading on case deletion).
* **`Procedure` → `CommitteeRecommendation`**: One-to-Many (`Procedure` is protected from deletion).
* **`CommitteeCase` → `Referral`**: One-to-Many (a case can have referrals issued; cascading on case deletion).
* **`ReferralCenter` → `Referral`**: One-to-Many (`ReferralCenter` is protected from deletion).

---

## 5. Main Workflows and URL Structure

### 5.1 Route Map

All business routes are governed by Django authentication (`login_required` or `LoginRequiredMixin`).

| URL Pattern | View Name / Class | Route Name | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | `views.home` | `home` | Main dashboard |
| `/login/` | `auth_views.LoginView` | `login` | Authentication entry point |
| `/logout/` | `auth_views.LogoutView` | `logout` | Session termination |
| `/patients/` | `views.PatientListView` | `patient_list` | Paginated patient directory with search |
| `/patients/add/` | `views.patient_create` | `patient_create` | New patient registration |
| `/patients/<int:pk>/` | `views.patient_detail` | `patient_detail` | Patient profile and session enrollment |
| `/patients/<int:pk>/edit/` | `views.PatientUpdateView` | `patient_update` | Patient profile modification |
| `/patients/<int:pk>/add-to-session/` | `views.add_patient_to_session` | `add_patient_to_session` | Add patient to active `PREPARING` session |
| `/sessions/` | `views.CommitteeSessionListView` | `session_list` | Chronological list of committee sessions |
| `/sessions/create/` | `views.CommitteeSessionCreateView`| `session_create` | Schedule a new session |
| `/session/<int:pk>` | `views.CommitteeSessionDetailView`| `session_detail` | Session view, cases roster, and actions |
| `/sessions/<int:pk>/recommendations/`| `views.session_recommendations`| `session_recommendations` | Multi-case decision entry form |
| `/sessions/<int:pk>/complete/` | `views.session_complete` | `session_complete` | Validate and close session |
| `/sessions/<int:pk>/print/` | `views.session_print` | `session_print` | Printable committee session roster |
| `/cases/<int:case_pk>/recommendation/print/` | `views.recommendation_print` | `recommendation_print` | Printable recommendation decision memo |
| `/referrals/pending/` | `views.pending_referrals` | `pending_referrals` | Queue of cases requiring referral issuance |
| `/referrals/create/<int:case_pk>/` | `views.referral_create` | `referral_create` | Issue referral letter for approved case |
| `/referrals/<int:pk>/` | `views.referral_detail` | `referral_detail` | View issued referral letter details |
| `/referrals/<int:pk>/edit/` | `views.referral_update` | `referral_update` | Change referral destination center |
| `/referrals/<int:pk>/cancel/` | `views.referral_cancel` | `referral_cancel` | Cancel referral with required reason |
| `/referrals/<int:pk>/print/` | `views.referral_print` | `referral_print` | Official printable referral letter |

### 5.2 Core Operational Workflows

1. **Patient Onboarding**:
   * Patient profile is created via `patient_create` with validation for unique 14-digit Egyptian National ID.
   * Search interface filters by full name or national ID with 25-record pagination.

2. **Session Lifecycle & Patient Scheduling**:
   * A session is initiated with a designated `session_date` and consultant `doctor`, defaulting to status `PREPARING`.
   * From the patient profile, staff click "إضافة إلى الجلسة" (`add_patient_to_session`), automatically enrolling the patient into the currently open `PREPARING` session as a `PENDING` case.

3. **Committee Review & Decision Entry**:
   * Inside `session_recommendations`, all cases in the session are displayed with prefixed sub-forms (`case_<id>`).
   * Staff select the recommended `Procedure`, specify `no_of_sessions` (1–10), and enter `recommendation_text`.
   * Submitting updates the `CommitteeRecommendation` and transitions the `CommitteeCase.status` to `APPROVED`.

4. **Session Finalization (Completion Gate)**:
   * When invoking `session_complete`, the system inspects every case in the session.
   * If any case lacks a recommendation or procedure, completion is blocked with a descriptive error message.
   * If all cases are complete, the session status transitions to `COMPLETED`.

5. **Referral Dispatch & Tracking**:
   * The `pending_referrals` view queries approved cases where `procedure.requires_referral == True` that have no existing referral.
   * Operators issue a referral directed to an authorized `ReferralCenter`.
   * If circumstances change, the referral can be edited or cancelled via `referral_cancel` with an audit-recorded cancellation reason.

---

## 6. Template Inventory and Important Files

### 6.1 Template Hierarchy (`committee/templates/`)

```
templates/
├── base.html                               # Base skeleton (header, navigation, auth state, flash messages)
├── home.html                               # Main navigation dashboard
├── registration/
│   └── login.html                          # User authentication form
├── patients/
│   ├── patient_list.html                   # Patient table, search bar, pagination controls
│   ├── patient_form.html                   # Create and edit patient form
│   └── patient_detail.html                 # Patient overview, case history, add-to-session action
├── sessions/
│   ├── session_list.html                   # List of sessions with status badges and preparing-session alert
│   ├── session_create.html                 # Session creation form (date and consultant doctor)
│   ├── session_detail.html                 # Roster of patients in session with status controls
│   ├── session_recommendations.html        # Multi-case batch recommendation form
│   ├── session_print.html                  # Formal printable session report for official records
│   └── recommendation_print.html           # Individual printable recommendation slip
└── referrals/
    ├── pending_referrals.html              # Pending referral issuance queue + past referrals log
    ├── referral_create.html                # Referral letter issuance form
    ├── referral_detail.html                # Referral letter preview
    ├── referral_update.html                # Edit destination center
    ├── referral_cancel.html                # Cancellation reason dialog
    └── referral_print.html                 # Formal printable referral letter
```

### 6.2 Key Supporting Files

* **`committee/constants.py`**: Central repository for application constants and textual choices in Arabic (`Gender`, `Branches`, `InsuranceLaw`, `SessionStatus`, `CaseStatus`, `ReferralStatus`).
* **`committee/forms.py`**: Django ModelForms with Arabic labels, widget styling, and constraints (`PatientForm`, `ProcedureForm`, `DoctorForm`, `CommitteeSessionForm`, `CommitteeRecommendationForm`, `ReferralCenterForm`, `ReferralForm`, `ReferralCancelForm`).
* **`committee/admin.py`**: Model registration for Django Admin. Includes custom `ReferralCenterAdmin` with filters and list-editable flags for `for_gamma` and `for_bone_marrow`.
* **Static Assets (`committee/static/`)**:
  * `css/main.css`: Base application styles, Arabic RTL layout, buttons, and form components.
  * `css/home.css`: Dashboard grid styling.
  * `css/print.css`: Print media styles formatting session summaries for physical paper.
  * `css/referral_print.css`: Print media styles specifically formatted for official referral letters.
  * `images/`: Logo, background, and iconography (`pts_icon.png`, `session_icon.png`, `referral_icon.png`).
* **`GamaKnifeSystem_start.bat`**: Windows batch script automating virtual environment activation, browser launch, and server startup (`python manage.py runserver`).
* **`requirements.txt`**: Minimal production dependency lock (`Django==5.2.17`, `asgiref==3.12.1`, `sqlparse==0.5.5`, `tzdata==2026.3`).

# Sparsa Homeoclinic — Test Credentials

Seeded on backend startup. Login via POST /api/auth/login with `{username, password}`.

| Username    | Password       | Role          | Display Name        | Dashboard         |
|-------------|----------------|---------------|---------------------|-------------------|
| admin1      | Password@123   | ADMIN         | System Admin        | /admin            |
| jyothi      | Password@123   | OWNER_DOCTOR  | Dr. Jyothi Vani     | /doctor           |
| hemanth     | Password@123   | DOCTOR        | Dr. Hemanth         | /doctor           |
| reception1  | Password@123   | RECEPTION     | Reception Desk      | /reception        |
| pharmacy1   | Password@123   | PHARMACY      | Pharmacy Counter    | /pharmacy         |
| pro1        | Password@123   | PRO           | Billing Desk        | /pro              |

## Auth endpoints
- POST `/api/auth/login` — body: `{ "username": "...", "password": "..." }` → sets httpOnly access_token + refresh_token cookies, returns user object
- GET  `/api/auth/me` — returns current user
- POST `/api/auth/logout` — clears cookies

## Notes
- Roles enforced server-side. OWNER_DOCTOR (Jyothi) can see all cases including Hemanth's.
- DOCTOR (Hemanth) can only see his own assigned cases.
- ADMIN has full read access to all data and exclusive access to user management + audit logs + stats.

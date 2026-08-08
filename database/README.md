# Database

Contains the offline-first SQLite schema and, later, versioned migrations. `schema.sql` is the initial database contract for residents, disposal events, users, and Firebase sync work.

Apply the schema to a new local database with `sqlite3 smartseg.db ".read database/schema.sql"`.

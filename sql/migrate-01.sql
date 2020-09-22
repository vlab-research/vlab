-- CREATE TABLE chatroach.projects(
--        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--        name VARCHAR NOT NULL
-- );

-- CREATE TABLE chatroach.users_projects(
--        userid UUID NOT NULL REFERENCES chatroach.users(id) ON DELETE CASCADE,
--        projectid UUID NOT NULL REFERENCES chatroach.projects(id) ON DELETE CASCADE
-- );

ALTER TABLE chatroach.facebook_pages ADD COLUMN token VARCHAR;
-- ALTER TABLE chatroach.facebook_pages ADD COLUMN projectid UUID REFERENCES chatroach.projects(id) ON DELETE CASCADE;


-- ALTER TABLE chatroach.surveys ADD COLUMN projectid UUID REFERENCES chatroach.projects(id) ON DELETE CASCADE;

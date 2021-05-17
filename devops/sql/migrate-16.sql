CREATE INDEX ON chatroach.messages (timestamp DESC) STORING (content);

-- REMOVE TOKEN FROM USERS AND ADD TO CREDENTIALS
SET sql_safe_updates=false;
ALTER TABLE chatroach.users DROP COLUMN token;
SET sql_safe_updates=true;

DROP TABLE chatroach.timeouts;
DROP TABLE chatroach.facebook_pages;

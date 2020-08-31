-- messages updates!

-- fix weird farmhash int and make reasonable primary key!
ALTER TABLE chatroach.messages ADD COLUMN hsh INT AS (fnv64a(content)) STORED NOT NULL;
BEGIN;
ALTER TABLE chatroach.messages DROP CONSTRAINT "primary";
ALTER TABLE chatroach.messages ADD CONSTRAINT "primary" PRIMARY KEY (hsh, userid);
COMMIT;

ALTER TABLE chatroach.messages ALTER COLUMN id DROP NOT NULL;

-- indices
CREATE INDEX ON chatroach.messages (userid, timestamp ASC) STORING (content);

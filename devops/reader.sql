CREATE USER chatreader;
GRANT SELECT ON TABLE chatroach.messages to chatreader;
GRANT SELECT ON TABLE chatroach.responses to chatreader;
GRANT SELECT ON TABLE chatroach.timeouts to chatreader;
GRANT SELECT ON TABLE chatroach.surveys to chatreader;
GRANT SELECT ON TABLE chatroach.states to chatreader;

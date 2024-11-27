SELECT * FROM motion_detectors

CREATE TABLE motion_detectors(
 id SERIAL PRIMARY KEY,
 date_data DATETIME,
 message VARCHAR(255)
);
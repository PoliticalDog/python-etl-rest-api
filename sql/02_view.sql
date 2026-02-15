-- Vistas
USE pt_db;

CREATE OR REPLACE VIEW daily_company_totals AS
SELECT
    c.company_name,
    DATE(ch.created_at) AS transaction_date,
    SUM(ch.amount) AS total_amount
FROM charges ch
JOIN companies c ON ch.company_id = c.company_id
GROUP BY c.company_name, DATE(ch.created_at);


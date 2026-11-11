-- The daily retention job deletes cost-ledger rows older than 13 months.
-- Only the trusted system context may delete; readers can still only insert.
GRANT DELETE ON llm_calls TO letterlens_app;
CREATE POLICY llm_calls_system_delete ON llm_calls FOR DELETE USING (app_is_system());

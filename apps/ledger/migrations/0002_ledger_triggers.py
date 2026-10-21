"""Triggers de PostgreSQL para el libro mayor.

- ``ledger_assert_balanced`` + constraint trigger diferido: garantiza que toda
  transacción tenga ``sum(debits) = sum(credits)`` al commit.
- ``ledger_prevent_mutation``: bloquea ``UPDATE`` y ``DELETE`` sobre
  ``LedgerTransaction`` y ``LedgerEntry`` (inmutabilidad, AGENTS §6 regla 4).
"""

from django.db import migrations

CREATE_ASSERT_BALANCED = """
CREATE OR REPLACE FUNCTION ledger_assert_balanced(target_transaction_id uuid)
RETURNS void AS $$
DECLARE
    debit_total numeric;
    credit_total numeric;
BEGIN
    SELECT
        COALESCE(SUM(amount) FILTER (WHERE direction = 'debit'), 0),
        COALESCE(SUM(amount) FILTER (WHERE direction = 'credit'), 0)
    INTO debit_total, credit_total
    FROM ledger_ledgerentry
    WHERE ledger_transaction_id = target_transaction_id;

    IF debit_total <> credit_total THEN
        RAISE EXCEPTION
            'Ledger transaction % is not balanced (debits=%, credits=%)',
            target_transaction_id, debit_total, credit_total
            USING ERRCODE = '23514';
    END IF;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_ENTRY_BALANCED_TRIGGER = """
CREATE OR REPLACE FUNCTION ledger_trigger_check_entry_balanced() RETURNS trigger AS $$
BEGIN
    PERFORM ledger_assert_balanced(NEW.ledger_transaction_id);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_PREVENT_MUTATION = """
CREATE OR REPLACE FUNCTION ledger_prevent_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        '% rows are immutable: % is not allowed',
        TG_TABLE_NAME, TG_OP
        USING ERRCODE = '23514';
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGERS = [
    """
    CREATE CONSTRAINT TRIGGER ledger_entry_balanced
    AFTER INSERT ON ledger_ledgerentry
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION ledger_trigger_check_entry_balanced();
    """,
    """
    CREATE TRIGGER ledger_transaction_immutable
    BEFORE UPDATE OR DELETE ON ledger_ledgertransaction
    FOR EACH ROW EXECUTE FUNCTION ledger_prevent_mutation();
    """,
    """
    CREATE TRIGGER ledger_entry_immutable
    BEFORE UPDATE OR DELETE ON ledger_ledgerentry
    FOR EACH ROW EXECUTE FUNCTION ledger_prevent_mutation();
    """,
]

DROP_TRIGGERS = [
    'DROP TRIGGER IF EXISTS ledger_entry_balanced ON ledger_ledgerentry;',
    'DROP TRIGGER IF EXISTS ledger_transaction_immutable ON ledger_ledgertransaction;',
    'DROP TRIGGER IF EXISTS ledger_entry_immutable ON ledger_ledgerentry;',
]


class Migration(migrations.Migration):
    dependencies = [
        ('ledger', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                CREATE_ASSERT_BALANCED,
                CREATE_ENTRY_BALANCED_TRIGGER,
                CREATE_PREVENT_MUTATION,
                *CREATE_TRIGGERS,
            ],
            reverse_sql=[
                *DROP_TRIGGERS,
                'DROP FUNCTION IF EXISTS ledger_trigger_check_entry_balanced();',
                'DROP FUNCTION IF EXISTS ledger_prevent_mutation();',
                'DROP FUNCTION IF EXISTS ledger_assert_balanced(uuid);',
            ],
        ),
    ]

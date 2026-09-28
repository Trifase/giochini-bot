import os
import sys
import sqlite3
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ask_ai import clean_sql_output, execute_readonly_sql


def test_clean_sql_output():
    raw_markdown = "```sql\nSELECT * FROM punteggi;\n```"
    assert clean_sql_output(raw_markdown) == "SELECT * FROM punteggi"

    raw_markdown_no_lang = "```\nSELECT game, COUNT(*) FROM punteggi\n```"
    assert clean_sql_output(raw_markdown_no_lang) == "SELECT game, COUNT(*) FROM punteggi"

    plain = "  SELECT user_name FROM punteggi;  "
    assert clean_sql_output(plain) == "SELECT user_name FROM punteggi"


def test_execute_readonly_sql_valid(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE punteggi (game TEXT, tries INT)")
    conn.execute("INSERT INTO punteggi VALUES ('Wordle', 3)")
    conn.execute("INSERT INTO punteggi VALUES ('Wordle', 4)")
    conn.commit()
    conn.close()

    cols, rows = execute_readonly_sql(str(db_file), "SELECT game, COUNT(*) FROM punteggi GROUP BY game")
    assert cols == ["game", "COUNT(*)"]
    assert rows == [("Wordle", 2)]


def test_execute_readonly_sql_blocks_mutations(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE punteggi (game TEXT, tries INT)")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="Sono consentite esclusivamente query SELECT o WITH"):
        execute_readonly_sql(str(db_file), "DELETE FROM punteggi")

    with pytest.raises(ValueError, match="Parola chiave non permessa"):
        execute_readonly_sql(str(db_file), "SELECT * FROM punteggi; DROP TABLE punteggi")

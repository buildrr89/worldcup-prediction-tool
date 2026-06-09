"""Unit tests for the Football-Data.co.uk CSV importer (`src/importers/football_data_csv.py`).

Standard library `unittest` only. Run from the repo root:

    python3 -m unittest tests/test_football_data_csv.py
"""

import sys
import unittest
import tempfile
from pathlib import Path

# Set up project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.importers.football_data_csv import (
    parse_result,
    parse_float,
    row_to_historical_match,
    load_csv,
    load_csv_file,
    summarise_historical_matches,
    backtest_baseline,
)


class TestFootballDataCSVImporter(unittest.TestCase):
    def test_1_parse_result_valid(self):
        """parse_result maps H/D/A correctly and is case-insensitive, stripping whitespace."""
        self.assertEqual(parse_result("H"), "home")
        self.assertEqual(parse_result("D"), "draw")
        self.assertEqual(parse_result("A"), "away")
        self.assertEqual(parse_result(" h "), "home")
        self.assertEqual(parse_result("d\n"), "draw")
        self.assertEqual(parse_result("\ta"), "away")

    def test_2_parse_result_invalid(self):
        """parse_result rejects invalid values by raising ValueError."""
        with self.assertRaises(ValueError):
            parse_result("X")
        with self.assertRaises(ValueError):
            parse_result("")
        with self.assertRaises(ValueError):
            # Non-string inputs should raise ValueError
            parse_result(None)  # type: ignore
        with self.assertRaises(ValueError):
            parse_result(123)  # type: ignore

    def test_3_parse_float(self):
        """parse_float handles normal numeric strings, blanks, and invalid values."""
        # Valid float strings
        self.assertEqual(parse_float("2.5"), 2.5)
        self.assertEqual(parse_float(" 10 "), 10.0)
        self.assertEqual(parse_float(1.85), 1.85)

        # Blanks
        self.assertIsNone(parse_float(""))
        self.assertIsNone(parse_float("   "))
        self.assertIsNone(parse_float(None))

        # Invalid non-empty numeric-looking values
        with self.assertRaises(ValueError):
            parse_float("abc")
        with self.assertRaises(ValueError):
            parse_float("1.2.3")
        with self.assertRaises(ValueError):
            parse_float(True)  # type: ignore

    def test_4_row_to_historical_match_valid(self):
        """row_to_historical_match returns a clean dictionary for a valid row with B365 odds."""
        row = {
            "Date": "18/12/2022",
            "HomeTeam": "Argentina",
            "AwayTeam": "France",
            "FTR": "D",
            "B365H": "2.80",
            "B365D": "3.00",
            "B365A": "2.80",
        }
        match = row_to_historical_match(row, odds_prefix="B365")
        self.assertIsNotNone(match)
        self.assertEqual(match["date"], "18/12/2022")
        self.assertEqual(match["home_team"], "Argentina")
        self.assertEqual(match["away_team"], "France")
        self.assertEqual(match["actual_result"], "draw")
        self.assertEqual(match["home_decimal_odds"], 2.80)
        self.assertEqual(match["draw_decimal_odds"], 3.00)
        self.assertEqual(match["away_decimal_odds"], 2.80)
        self.assertEqual(match["source"], "football-data.co.uk")
        self.assertEqual(match["odds_prefix"], "B365")
        
        # De-vigged probabilities must sum to ~1.0
        baseline = match["baseline"]
        self.assertAlmostEqual(baseline["home"] + baseline["draw"] + baseline["away"], 1.0)
        # Margin should be present and positive
        self.assertGreater(match["margin"], 0.0)

    def test_5_row_to_historical_match_missing_odds(self):
        """row_to_historical_match returns None when any bookmaker odds are missing or blank."""
        base_row = {
            "Date": "18/12/2022",
            "HomeTeam": "Argentina",
            "AwayTeam": "France",
            "FTR": "D",
        }

        # Missing odds key entirely
        row1 = base_row.copy()
        row1["B365H"] = "2.80"
        row1["B365D"] = "3.00"
        # B365A missing
        self.assertIsNone(row_to_historical_match(row1))

        # Blank odds value
        row2 = base_row.copy()
        row2["B365H"] = "2.80"
        row2["B365D"] = " "
        row2["B365A"] = "2.80"
        self.assertIsNone(row_to_historical_match(row2))

    def test_6_row_to_historical_match_missing_required(self):
        """row_to_historical_match returns None when required team/result/date fields are missing or blank."""
        row = {
            "Date": "18/12/2022",
            "HomeTeam": "Argentina",
            "AwayTeam": "France",
            "FTR": "D",
            "B365H": "2.80",
            "B365D": "3.00",
            "B365A": "2.80",
        }

        for field in ["Date", "HomeTeam", "AwayTeam", "FTR"]:
            # Test key missing
            bad_row1 = row.copy()
            del bad_row1[field]
            self.assertIsNone(row_to_historical_match(bad_row1))

            # Test value blank
            bad_row2 = row.copy()
            bad_row2[field] = " "
            self.assertIsNone(row_to_historical_match(bad_row2))

    def test_7_load_csv_skips_and_loads(self):
        """load_csv loads multiple valid rows and skips rows that return None."""
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
            "21/11/2022,England,Iran,,3.20,3.10,2.40\n"  # Missing FTR -> Skip
            "21/11/2022,Senegal,Netherlands,A,6.00,3.80,1.60\n"
            "22/11/2022,Argentina,Saudi Arabia,A,1.15,8.00,19.00\n"
        )
        
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as tmp:
            tmp.write(csv_data)
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            matches = load_csv(tmp_path)
            # Expect 3 matches loaded, 1 skipped (row with missing FTR)
            self.assertEqual(len(matches), 3)
            self.assertEqual(matches[0]["home_team"], "Qatar")
            self.assertEqual(matches[1]["home_team"], "Senegal")
            self.assertEqual(matches[2]["home_team"], "Argentina")
        finally:
            tmp_path.unlink()

    def test_8_load_csv_error_line_number(self):
        """load_csv raises ValueError with the correct line number on invalid present numeric values."""
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
            "21/11/2022,England,Iran,H,1.15,abc,19.00\n"  # abc is invalid odds -> Row 3
        )
        
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as tmp:
            tmp.write(csv_data)
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ValueError) as ctx:
                load_csv(tmp_path)
            # Line number in file: Row 1 is header, Row 2 is Qatar/Ecuador, Row 3 is England/Iran
            # csv.DictReader's reader.line_num should be 3
            self.assertIn("Row 3", str(ctx.exception))
        finally:
            tmp_path.unlink()

    def test_9_summarise_historical_matches(self):
        """summarise_historical_matches calculates count, results, and average margin correctly."""
        # Setup mock matches with manual margins:
        # Match 1: odds (2.0, 3.0, 6.0) -> raw sum = 0.5 + 0.333 + 0.1667 = 1.0 -> margin = 0.0
        # Match 2: odds (2.0, 4.0, 4.0) -> raw sum = 0.5 + 0.25 + 0.25 = 1.0 -> margin = 0.0
        # Let's just use realistic de-vig outputs
        matches = [
            {"actual_result": "home", "margin": 0.05},
            {"actual_result": "draw", "margin": 0.07},
            {"actual_result": "away", "margin": 0.09},
            {"actual_result": "home", "margin": 0.03},
        ]
        
        summary = summarise_historical_matches(matches)
        self.assertEqual(summary["match_count"], 4)
        self.assertEqual(summary["home_wins"], 2)
        self.assertEqual(summary["draws"], 1)
        self.assertEqual(summary["away_wins"], 1)
        # Average margin: (0.05 + 0.07 + 0.09 + 0.03) / 4 = 0.24 / 4 = 0.06
        self.assertAlmostEqual(summary["average_margin"], 0.06)

    def test_10_backtest_baseline(self):
        """backtest_baseline calculates average Brier score and log loss correctly."""
        # Match 1: result "home", baseline home = 0.6, draw = 0.2, away = 0.2
        # Brier: (0.6-1.0)^2 + (0.2-0)^2 + (0.2-0)^2 = 0.16 + 0.04 + 0.04 = 0.24
        # Log Loss: -log(0.6) = 0.51082562376
        # Match 2: result "draw", baseline home = 0.3, draw = 0.4, away = 0.3
        # Brier: (0.3-0)^2 + (0.4-1.0)^2 + (0.3-0)^2 = 0.09 + 0.36 + 0.09 = 0.54
        # Log Loss: -log(0.4) = 0.91629073187
        
        matches = [
            {
                "actual_result": "home",
                "baseline": {"home": 0.6, "draw": 0.2, "away": 0.2},
            },
            {
                "actual_result": "draw",
                "baseline": {"home": 0.3, "draw": 0.4, "away": 0.3},
            },
        ]
        
        results = backtest_baseline(matches)
        self.assertEqual(results["match_count"], 2)
        # Average Brier: (0.24 + 0.54) / 2 = 0.39
        self.assertAlmostEqual(results["average_brier"], 0.39)
        # Average Log Loss: (0.51082562376 + 0.91629073187) / 2 = 0.71355817781
        self.assertAlmostEqual(results["average_log_loss"], 0.71355817781)

    def test_11_empty_summary_and_backtest(self):
        """Empty list inputs to summarize and backtest return zeroed metrics."""
        summary = summarise_historical_matches([])
        self.assertEqual(summary["match_count"], 0)
        self.assertEqual(summary["home_wins"], 0)
        self.assertEqual(summary["draws"], 0)
        self.assertEqual(summary["away_wins"], 0)
        self.assertEqual(summary["average_margin"], 0.0)

        backtest = backtest_baseline([])
        self.assertEqual(backtest["match_count"], 0)
        self.assertEqual(backtest["average_brier"], 0.0)
        self.assertEqual(backtest["average_log_loss"], 0.0)

    def test_12_alternative_odds_prefix(self):
        """Alternative odds prefixes work (e.g., Pinnacle PSH, PSD, PSA)."""
        row = {
            "Date": "18/12/2022",
            "HomeTeam": "Argentina",
            "AwayTeam": "France",
            "FTR": "D",
            "PSH": "2.80",
            "PSD": "3.00",
            "PSA": "2.80",
        }
        match = row_to_historical_match(row, odds_prefix="PS")
        self.assertIsNotNone(match)
        self.assertEqual(match["home_decimal_odds"], 2.80)
        self.assertEqual(match["draw_decimal_odds"], 3.00)
        self.assertEqual(match["away_decimal_odds"], 2.80)
        self.assertEqual(match["odds_prefix"], "PS")

    def test_13_load_csv_file_string_io(self):
        """load_csv_file works with io.StringIO."""
        import io
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
            "21/11/2022,England,Iran,H,1.15,3.80,19.00\n"
        )
        file_obj = io.StringIO(csv_data)
        matches = load_csv_file(file_obj)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["home_team"], "Qatar")
        self.assertEqual(matches[1]["home_team"], "England")

    def test_14_load_csv_file_bytes_io(self):
        """load_csv_file works with io.BytesIO."""
        import io
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
            "21/11/2022,England,Iran,H,1.15,3.80,19.00\n"
        )
        file_obj = io.BytesIO(csv_data.encode("utf-8-sig"))
        matches = load_csv_file(file_obj)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["home_team"], "Qatar")

    def test_15_load_csv_file_bytes_direct(self):
        """load_csv_file works with direct bytes input."""
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
        )
        matches = load_csv_file(csv_data.encode("utf-8"))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["home_team"], "Qatar")

    def test_16_load_csv_file_skips_incomplete(self):
        """load_csv_file skips incomplete rows (missing/blank fields)."""
        import io
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
            "21/11/2022,England,Iran,,1.15,3.80,19.00\n"  # Missing FTR
            "22/11/2022,Senegal,,A,6.00,3.80,1.60\n"      # Missing AwayTeam
        )
        file_obj = io.StringIO(csv_data)
        matches = load_csv_file(file_obj)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["home_team"], "Qatar")

    def test_17_load_csv_file_error_line_number(self):
        """load_csv_file includes the correct row number in invalid numeric value errors."""
        import io
        csv_data = (
            "Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A\n"
            "20/11/2022,Qatar,Ecuador,A,3.20,3.10,2.40\n"
            "21/11/2022,England,Iran,H,1.15,abc,19.00\n"  # Invalid odds on Row 3
        )
        file_obj = io.StringIO(csv_data)
        with self.assertRaises(ValueError) as ctx:
            load_csv_file(file_obj)
        self.assertIn("Row 3", str(ctx.exception))

    def test_18_sample_csv_compatibility(self):
        """Verify the synthetic sample CSV loads successfully, has at least 8 rows, and passes summary/backtest."""
        sample_path = Path(__file__).resolve().parent.parent / "sample_data" / "football_data_sample.csv"
        self.assertTrue(sample_path.exists(), f"Sample CSV file does not exist at {sample_path}")
        
        matches = load_csv(sample_path, odds_prefix="B365")
        
        # verifies at least 8 parsed rows
        self.assertGreaterEqual(len(matches), 8)
        
        # verifies summarise_historical_matches returns non-zero match_count
        summary = summarise_historical_matches(matches)
        self.assertEqual(summary["match_count"], len(matches))
        self.assertGreater(summary["match_count"], 0)
        
        # verifies backtest_baseline returns non-zero match_count
        backtest = backtest_baseline(matches)
        self.assertEqual(backtest["match_count"], len(matches))
        self.assertGreater(backtest["match_count"], 0)
        
        # verifies all parsed team names are synthetic/fake by checking they are from an allowlist used in the sample
        allowlist = {
            "Alpha FC",
            "Beta United",
            "Gamma City",
            "Delta Rovers",
            "Echo Town",
            "Foxtrot Athletic",
            "Nova XI",
            "Orion Club"
        }
        for match in matches:
            self.assertIn(match["home_team"], allowlist)
            self.assertIn(match["away_team"], allowlist)


if __name__ == "__main__":
    unittest.main()

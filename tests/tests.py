"""
Tests for AWS Resume Parser Lambda function.

Setup:
  pip install pytest

Run with:
  pytest test_lambda_function.py -v

Note: assumes lambda_function.py lives at lambda/lambda_function.py relative
to the repo root. Adjust the sys.path line below if your layout differs.
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

from lambda_function import extract_entities, lambda_handler


class TestExtractEntities:

    def test_extracts_known_skills(self):
        text = "Experienced with Python, React, and Docker in production."
        skills, names = extract_entities(text)
        assert "Python" in skills
        assert "React" in skills
        assert "Docker" in skills

    def test_ignores_skills_not_present(self):
        text = "I only know Python."
        skills, _ = extract_entities(text)
        assert "Java" not in skills
        assert "Kubernetes" not in skills

    def test_case_insensitive_matching(self):
        text = "javascript AND PYTHON and react"
        skills, _ = extract_entities(text)
        assert "JavaScript" in skills
        assert "Python" in skills
        assert "React" in skills

    def test_word_boundary_avoids_partial_matches(self):
        text = "I work with CSS and React daily."
        skills, _ = extract_entities(text)
        assert "CSS" in skills
        # "C" alone shouldn't spuriously match inside "CSS"/"CSharp" etc.
        assert skills.count("C") <= 1

    def test_empty_text_returns_no_skills_and_unknown_name(self):
        skills, names = extract_entities("")
        assert skills == []
        assert names == ["Unknown"]

    def test_extracts_first_short_line_as_name(self):
        text = "Jane Doe\nSoftware Engineer\nPython, React, AWS"
        skills, names = extract_entities(text)
        assert names[0] == "Jane Doe"

    def test_skips_blank_lines_when_finding_name(self):
        text = "\n\n   \nJohn Smith\nContact: john@example.com"
        skills, names = extract_entities(text)
        assert names[0] == "John Smith"

    def test_falls_back_to_unknown_if_no_short_line(self):
        text = (
            "This is a very long line that has way more than four words in it\n"
            "Another long line here too with plenty more words than allowed"
        )
        skills, names = extract_entities(text)
        assert names[0] == "Unknown"


class TestLambdaHandler:

    @patch("lambda_function.table")
    @patch("lambda_function.fitz")
    @patch("lambda_function.s3")
    def test_processes_resume_and_writes_to_dynamodb(self, mock_s3, mock_fitz, mock_table):
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "resumes/test.pdf"},
                }
            }]
        }

        mock_page = MagicMock()
        mock_page.get_text.return_value = "Jane Doe\nPython, React, AWS"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value = mock_doc

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        mock_s3.download_file.assert_called_once_with(
            "test-bucket", "resumes/test.pdf", "/tmp/resume.pdf"
        )
        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["candidateName"] == "Jane Doe"
        assert "Python" in item["skills"]
        assert item["sourceFile"] == "s3://test-bucket/resumes/test.pdf"

    @patch("lambda_function.table")
    @patch("lambda_function.fitz")
    @patch("lambda_function.s3")
    def test_handles_resume_with_no_recognizable_skills(self, mock_s3, mock_fitz, mock_table):
        event = {
            "Records": [{
                "s3": {"bucket": {"name": "b"}, "object": {"key": "k.pdf"}}
            }]
        }
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Just a hobbyist, no tech skills listed."
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value = mock_doc

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["skills"] == []
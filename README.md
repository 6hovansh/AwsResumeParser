# AWS Resume Parser

A serverless resume parser built using AWS.

## Features

- Upload PDF resumes to Amazon S3
- Trigger AWS Lambda automatically
- Extract text using PyMuPDF
- Extract candidate name and skills
- Store data in DynamoDB

## Tech Stack

- Python
- AWS Lambda
- Amazon S3
- Amazon DynamoDB
- PyMuPDF

## Architecture

S3
 ↓
Lambda
 ↓
PyMuPDF
 ↓
Skill Extraction
 ↓
DynamoDB
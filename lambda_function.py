import boto3
import uuid
import fitz
import re

print(fitz.__doc__)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("ResumeData")


def extract_entities(text):
    common_skills = [
        "Python", "Java", "JavaScript", "TypeScript",
        "React", "Node.js", "Express", "MongoDB",
        "MySQL", "PostgreSQL", "SQL", "HTML", "CSS",
        "Bootstrap", "Tailwind", "AWS", "Docker",
        "Kubernetes", "Git", "GitHub", "Linux",
        "C", "C++", "C#", "PHP", "Angular", "Vue",
        "Firebase", "REST API", "GraphQL"
    ]

    skills = []

    text_lower = text.lower()

   for skill in common_skills:
    pattern = r"\b" + re.escape(skill.lower()) + r"\b"
    if re.search(pattern, text_lower):
        skills.append(skill)

    # Simple name extraction
    lines = text.split("\n")
    candidate_name = "Unknown"

    for line in lines:
        line = line.strip()
        if line and len(line.split()) <= 4:
            candidate_name = line
            break

    return skills, [candidate_name]


def lambda_handler(event, context):

    record = event["Records"][0]["s3"]

    bucket = record["bucket"]["name"]
    key = record["object"]["key"]

    local_file = "/tmp/resume.pdf"

    s3.download_file(bucket, key, local_file)

    doc = fitz.open(local_file)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    resume_id = str(uuid.uuid4())

    skills, names = extract_entities(text)

    table.put_item(
        Item={
            "resumeId": resume_id,
            "candidateName": names[0],
            "skills": skills,
            "sourceFile": f"s3://{bucket}/{key}"
        }
    )

    return {
        "statusCode": 200,
        "body": "Resume processed successfully"
    }
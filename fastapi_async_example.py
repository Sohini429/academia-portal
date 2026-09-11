"""
Step 6: Async Integration Example (Member 2 ke API mein isse jaisa kuch hoga)
-------------------------------------------------------------------------------
Ye sirf ek EXAMPLE hai ki tumhara pipeline FastAPI ke background task
ke saath kaise jud sakta hai, taaki upload request turant respond kare
aur extraction background mein chale (koi blocking na ho).

Isse tum Member 2 ko dikha sakti ho ki integration kaise expect kar rahi ho.
"""

import shutil
from fastapi import FastAPI, BackgroundTasks, UploadFile

from pipeline import run_pipeline

app = FastAPI()


def process_resume_in_background(pdf_path: str, student_id: str):
    result = run_pipeline(pdf_path, "skills_registry_sample.json")

    # TODO (Member 2 ke saath connect karna hai):
    # result["data"]["skill_ids"] ko student_skills table mein
    # student_id ke against save karna hai.
    print(f"Extracted for student {student_id}: {result['data']['skill_ids']}")
    if result["unmatched_terms"]:
        print(f"Unmatched terms to review: {result['unmatched_terms']}")


@app.post("/resume/upload")
async def upload_resume(student_id: str, file: UploadFile, background_tasks: BackgroundTasks):
    save_path = f"/tmp/{file.filename}"
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Turant respond karo, extraction background mein chale
    background_tasks.add_task(process_resume_in_background, save_path, student_id)

    return {
        "status": "success",
        "data": {"message": "Resume received, skill extraction started"},
        "timestamp": None,
        "errors": None,
    }

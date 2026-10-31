import uuid

from fastapi import APIRouter, BackgroundTasks, File, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import IngestionServiceDep, PaperServiceDep
from app.schemas.papers import JobOut, PaperList, PaperOut, UploadAccepted

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=UploadAccepted)
def upload_paper(
    background: BackgroundTasks,
    papers: PaperServiceDep,
    ingestion: IngestionServiceDep,
    file: UploadFile = File(..., description="Text-based PDF, max MAX_UPLOAD_MB"),
) -> UploadAccepted:
    paper, job = papers.create_from_upload(file)
    background.add_task(ingestion.run, job.id)
    return UploadAccepted(paper_id=paper.id, job_id=job.id, status=paper.status)


@router.get("", response_model=PaperList)
def list_papers(papers: PaperServiceDep) -> PaperList:
    return PaperList(items=[PaperOut.model_validate(p) for p in papers.list()])


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: uuid.UUID, papers: PaperServiceDep) -> PaperOut:
    return PaperOut.model_validate(papers.get(paper_id))


@router.get("/{paper_id}/file", response_class=FileResponse)
def get_paper_file(paper_id: uuid.UUID, papers: PaperServiceDep) -> FileResponse:
    paper = papers.get(paper_id)
    return FileResponse(
        papers.file_path(paper),
        media_type="application/pdf",
        filename=paper.original_filename,
        content_disposition_type="inline",
    )


@router.get("/{paper_id}/jobs/latest", response_model=JobOut)
def get_latest_job(paper_id: uuid.UUID, papers: PaperServiceDep) -> JobOut:
    return JobOut.model_validate(papers.latest_job(paper_id))


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(paper_id: uuid.UUID, papers: PaperServiceDep) -> Response:
    papers.delete(paper_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{paper_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadAccepted,
    responses={204: {"description": "A stuck deletion was completed"}},
)
def retry_paper(
    paper_id: uuid.UUID,
    background: BackgroundTasks,
    papers: PaperServiceDep,
    ingestion: IngestionServiceDep,
) -> UploadAccepted | Response:
    paper, job = papers.retry(paper_id)
    if job is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    background.add_task(ingestion.run, job.id)
    return UploadAccepted(paper_id=paper.id, job_id=job.id, status=paper.status)

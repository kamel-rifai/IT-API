from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import text
from typing import List

from .db import get_complaint_db, engine
from .schemas import ComplaintCreate, ComplaintResponse

# Apprise configuration: set APPRISE_URLS in env (comma-separated apprise service URLs)
APPRISE_URLS = "tgram://8028665172:AAHFj5vwi5HGKpgZTAbwaG4QakxlHjZhmvY/204621342"

router = APIRouter()

try:
    import apprise
except Exception:
    apprise = None


def notify_apprise(title: str, body: str):
    """Send a notification using Apprise if configured."""
    if not apprise:
        return
    if not APPRISE_URLS:
        return
    try:
        a = apprise.Apprise()
        for url in APPRISE_URLS.split(','):
            url = url.strip()
            if url:
                a.add(url)
        a.notify(title=title, body=body)
    except Exception:
        # swallow errors to avoid breaking main request flow
        return

# Configure these constants for your target list/board
TARGET_PROJECT_ID = 1700906029732070999
TARGET_BOARD_ID = 1700906101530166873
TARGET_LIST_ID = 1700907504793290333
DEFAULT_POSITION_INCREMENT = 65536.0
DEFAULT_CARD_TYPE = 'project'  # follow board's default_card_type


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(complaint: ComplaintCreate, background_tasks: BackgroundTasks, db=Depends(get_complaint_db)):
    """Create a new complaint as a card in the Planka `card` table under the specified list."""
    # Prepare name and description (embed reporter info if provided)
    name = complaint.name
    description_parts = []
    if complaint.reporter_name:
        description_parts.append(f"Reporter: {complaint.reporter_name}")
    if complaint.reporter_email:
        description_parts.append(f"Email: {complaint.reporter_email}")
    if complaint.description:
        description_parts.append(complaint.description)

    description = "\n\n".join(description_parts) if description_parts else None

    # Insert the card
    insert_sql = text(
        "INSERT INTO public.card (board_id, list_id, type, position, name, description, created_at, comments_total)"
        " VALUES (:board_id, :list_id, :type, :position, :name, :description, NOW(), 0)"
        " RETURNING id, board_id, list_id, type, position, name, description, created_at"
    )

    params = {
        'board_id': TARGET_BOARD_ID,
        'list_id': TARGET_LIST_ID,
        'type': DEFAULT_CARD_TYPE,
        'position': DEFAULT_POSITION_INCREMENT,
        'name': name,
        'description': description,
    }

    try:
        with db.begin():
            res = db.execute(insert_sql, params)
            row = res.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Failed to create complaint card")
            created = dict(row._mapping)

            # Schedule Apprise notification (if configured)
            msg_title = f"تم تقديم بلاغ جديد من:  {created['name']}"
            msg_body = f"ID: {created['id']}\n\n{created.get('description','') or ''}"
            background_tasks.add_task(notify_apprise, msg_title, msg_body)

            return ComplaintResponse(**{
                'id': created['id'],
                'board_id': created['board_id'],
                'list_id': created['list_id'],
                'name': created['name'],
                'description': created['description'],
                'created_at': created['created_at'].isoformat() if created.get('created_at') else None,
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ComplaintResponse])
def list_complaints(limit: int = 50, db=Depends(get_complaint_db)):
    """List recent complaints (cards) from the target list."""
    q = text("SELECT id, board_id, list_id, name, description, created_at FROM public.card WHERE list_id = :lid ORDER BY created_at DESC LIMIT :lim")
    rows = db.execute(q, {'lid': TARGET_LIST_ID, 'lim': limit}).mappings().fetchall()
    return [ComplaintResponse(**{
        'id': r['id'],
        'board_id': r['board_id'],
        'list_id': r['list_id'],
        'name': r['name'],
        'description': r.get('description'),
        'created_at': r['created_at'].isoformat() if r.get('created_at') else None,
    }) for r in rows]


@router.get("/{card_id}", response_model=ComplaintResponse)
def get_complaint(card_id: int, db=Depends(get_complaint_db)):
    q = text("SELECT id, board_id, list_id, name, description, created_at FROM public.card WHERE id = :id LIMIT 1")
    row = db.execute(q, {'id': card_id}).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Complaint not found')
    return ComplaintResponse(**{
        'id': row['id'],
        'board_id': row['board_id'],
        'list_id': row['list_id'],
        'name': row['name'],
        'description': row.get('description'),
        'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
    })

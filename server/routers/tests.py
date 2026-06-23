"""Definición de la batería de pruebas (§6.6)."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from server.auth import require_user
from server.db import get_session
from server.models import Measurement, Pattern, Test
from server.schemas import TestCreate, TestPatch

router = APIRouter(prefix="/api/tests", tags=["tests"])


def _slugify(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    return slug or "prueba"


def _unique_slug(session: Session, base: str) -> str:
    slug = base
    i = 2
    while session.get(Test, slug):
        slug = f"{base}-{i}"
        i += 1
    return slug


def _serialize(t: Test) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "pattern_id": t.pattern_id,
        "unit": t.unit,
        "better": t.better,
        "sort": t.sort,
        "archived": t.archived,
    }


@router.get("")
def list_tests(
    include_archived: bool = False,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    query = select(Test)
    if not include_archived:
        query = query.where(Test.archived == 0)
    rows = session.exec(query.order_by(Test.sort, Test.id)).all()
    return [_serialize(t) for t in rows]


@router.post("", status_code=201)
def create_test(
    payload: TestCreate,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    try:
        payload.validate_catalog()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not session.get(Pattern, payload.pattern_id):
        raise HTTPException(status_code=400, detail=f"Patrón inválido: {payload.pattern_id}")
    slug = _unique_slug(session, _slugify(payload.name))
    max_sort = session.exec(select(Test.sort).order_by(Test.sort.desc())).first()
    test = Test(
        id=slug,
        name=payload.name.strip(),
        pattern_id=payload.pattern_id,
        unit=payload.unit,
        better=payload.better,
        sort=(max_sort or 0) + 1,
        archived=0,
    )
    session.add(test)
    session.commit()
    return _serialize(test)


@router.patch("/{test_id}")
def patch_test(
    test_id: str,
    payload: TestPatch,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Prueba no encontrada")
    data = payload.model_dump(exclude_none=True)
    if "pattern_id" in data and not session.get(Pattern, data["pattern_id"]):
        raise HTTPException(status_code=400, detail=f"Patrón inválido: {data['pattern_id']}")
    from server.logic import VALID_BETTER, VALID_UNITS

    if "unit" in data and data["unit"] not in VALID_UNITS:
        raise HTTPException(status_code=400, detail=f"Unidad inválida: {data['unit']}")
    if "better" in data and data["better"] not in VALID_BETTER:
        raise HTTPException(status_code=400, detail=f"Dirección inválida: {data['better']}")
    for key in ("name", "pattern_id", "unit", "better", "sort"):
        if key in data:
            setattr(test, key, data[key])
    if "archived" in data:
        test.archived = 1 if data["archived"] else 0
    session.add(test)
    session.commit()
    return _serialize(test)


@router.delete("/{test_id}")
def delete_test(
    test_id: str,
    _=Depends(require_user),
    session: Session = Depends(get_session),
):
    """Soft delete si tiene mediciones; físico si no tiene ninguna."""
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Prueba no encontrada")
    has_measurements = session.exec(
        select(Measurement).where(Measurement.test_id == test_id).limit(1)
    ).first()
    if has_measurements:
        test.archived = 1
        session.add(test)
    else:
        session.delete(test)
    session.commit()
    return {"ok": True}

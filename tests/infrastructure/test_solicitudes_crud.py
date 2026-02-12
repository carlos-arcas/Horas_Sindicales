from __future__ import annotations


def test_crud_insert_update_delete_solicitud(
    solicitud_use_cases,
    solicitud_repo,
    solicitud_dto,
) -> None:
    creada, _ = solicitud_use_cases.agregar_solicitud(solicitud_dto)
    assert creada.id is not None

    solicitud_repo.update_pdf_info(creada.id, "/tmp/solicitud.pdf", "hash-123")
    persistida = solicitud_repo.get_by_id(creada.id)
    assert persistida is not None
    assert persistida.pdf_path == "/tmp/solicitud.pdf"
    assert persistida.pdf_hash == "hash-123"
    assert persistida.generated is True

    solicitud_use_cases.eliminar_solicitud(creada.id)
    assert solicitud_repo.get_by_id(creada.id) is None

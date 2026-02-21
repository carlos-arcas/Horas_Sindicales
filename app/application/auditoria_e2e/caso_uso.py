from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.application.auditoria_e2e.dto import (
    CheckAuditoria,
    ConflictosAuditoria,
    EstadoCheck,
    PlanAuditoria,
    RequestAuditoriaE2E,
    ResultadoAuditoria,
    RutasAuditoria,
)
from app.application.auditoria_e2e.puertos import HashPuerto, RelojPuerto, RepositorioInfoPuerto, SistemaArchivosPuerto
from app.application.auditoria_e2e.reglas import (
    evaluar_check_docs,
    evaluar_check_logging,
    evaluar_check_tests,
    evaluar_check_versionado,
    evaluar_check_windows_repro,
    evaluar_reglas_arquitectura,
)


class AuditarE2E:
    def __init__(
        self,
        *,
        reloj: RelojPuerto,
        fs: SistemaArchivosPuerto,
        repo_info: RepositorioInfoPuerto,
        hasher: HashPuerto,
    ) -> None:
        self._reloj = reloj
        self._fs = fs
        self._repo_info = repo_info
        self._hasher = hasher

    def obtener_plan(self, request: RequestAuditoriaE2E) -> PlanAuditoria:
        ahora = self._reloj.ahora_utc()
        audit_id = request.id_auditoria or f"AUD-{ahora.strftime('%Y%m%d-%H%M%S')}-{self._hasher.sha256_texto(ahora.isoformat())[:8]}"
        return PlanAuditoria(
            id_auditoria=audit_id,
            fecha_utc=ahora,
            dry_run=request.dry_run,
            checks_objetivo=[
                "CHECK-ARQ-001",
                "CHECK-TEST-001",
                "CHECK-LOG-001",
                "CHECK-WIN-001",
                "CHECK-DOC-001",
                "CHECK-VCS-001",
            ],
        )

    def obtener_rutas(self, plan: PlanAuditoria) -> RutasAuditoria:
        root = self._repo_info.obtener_info().root
        base = root / "logs" / "evidencias" / plan.id_auditoria
        return RutasAuditoria(
            base_dir=str(base),
            auditoria_md=str(base / "AUDITORIA.md"),
            auditoria_json=str(base / "auditoria.json"),
            manifest_json=str(base / "manifest.json"),
            status_txt=str(base / "status.txt"),
        )

    def validar_conflictos(self, plan: PlanAuditoria) -> ConflictosAuditoria:
        rutas = self.obtener_rutas(plan)
        conflictos: list[str] = []
        if self._fs.existe(Path(rutas.base_dir)):
            conflictos.append(f"Ya existe carpeta de evidencias para {plan.id_auditoria}")
        return ConflictosAuditoria(conflictos=conflictos)

    def ejecutar(self, request: RequestAuditoriaE2E) -> ResultadoAuditoria:
        plan = self.obtener_plan(request)
        rutas = self.obtener_rutas(plan)
        conflictos = self.validar_conflictos(plan).conflictos

        checks = self._ejecutar_checks()
        fallo = any(check.estado == EstadoCheck.FAIL for check in checks)
        score = self._calcular_score(checks)
        global_result = "FAIL" if fallo else "PASS"
        exit_code = 2 if fallo else 0

        repo = self._repo_info.obtener_info()
        payload = self.render_json(
            plan=plan,
            branch=repo.branch,
            commit=repo.commit,
            checks=checks,
            global_result=global_result,
            score=score,
            conflictos=conflictos,
            dry_run=request.dry_run,
            rutas=rutas,
            repo_root=repo.root,
        )
        contenido_md = self.render_markdown(
            plan=plan,
            branch=repo.branch,
            commit=repo.commit,
            checks=checks,
            global_result=global_result,
            score=score,
        )
        artefactos: list[str] = []

        if not request.dry_run:
            base = Path(rutas.base_dir)
            self._fs.mkdirs(base)
            self._fs.escribir_texto(Path(rutas.auditoria_md), contenido_md)
            auditoria_json = json.dumps(payload, indent=2, ensure_ascii=False)
            self._fs.escribir_texto(Path(rutas.auditoria_json), auditoria_json)
            self._fs.escribir_texto(Path(rutas.status_txt), global_result)

            manifest = self._manifest({
                "AUDITORIA.md": contenido_md,
                "auditoria.json": auditoria_json,
                "status.txt": global_result,
            })
            manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False)
            self._fs.escribir_texto(Path(rutas.manifest_json), manifest_text)
            artefactos = [rutas.auditoria_md, rutas.auditoria_json, rutas.manifest_json, rutas.status_txt]

        return ResultadoAuditoria(
            id_auditoria=plan.id_auditoria,
            dry_run=request.dry_run,
            resultado_global=global_result,
            exit_code=exit_code,
            score=score,
            checks=checks,
            rutas_previstas=rutas,
            conflictos=conflictos,
            contenido_md=contenido_md,
            contenido_json=payload,
            artefactos_generados=artefactos,
        )

    def render_json(
        self,
        *,
        plan: PlanAuditoria,
        branch: str | None,
        commit: str | None,
        checks: list[CheckAuditoria],
        global_result: str,
        score: float,
        conflictos: list[str],
        dry_run: bool,
        rutas: RutasAuditoria,
        repo_root: Path,
    ) -> dict[str, object]:
        backlog = [
            {
                "id_check": check.id_check,
                "severidad": check.severidad.value,
                "recomendacion": check.recomendacion,
            }
            for check in checks
            if check.estado == EstadoCheck.FAIL
        ]
        return {
            "metadatos": {
                "fecha_utc": plan.fecha_utc.isoformat(),
                "id_auditoria": plan.id_auditoria,
                "repo": {
                    "root": str(repo_root),
                    "branch": branch,
                    "commit": commit,
                },
                "dry_run": dry_run,
            },
            "resultado_global": global_result,
            "scorecard": {"nota_sobre_10": score},
            "checks": [asdict(check) for check in checks],
            "backlog_recomendado": backlog,
            "rutas_previstas": asdict(rutas),
            "conflictos": conflictos,
        }

    def _ejecutar_checks(self) -> list[CheckAuditoria]:
        root = self._repo_info.obtener_info().root
        return [
            evaluar_reglas_arquitectura(self._fs, root),
            evaluar_check_tests(self._fs, root),
            evaluar_check_logging(self._fs, root),
            evaluar_check_windows_repro(self._fs, root),
            evaluar_check_docs(self._fs, root),
            evaluar_check_versionado(self._fs, root),
        ]

    @staticmethod
    def _calcular_score(checks: list[CheckAuditoria]) -> float:
        score = 0.0
        for check in checks:
            if check.estado == EstadoCheck.PASS:
                score += 10 / len(checks)
            elif check.estado == EstadoCheck.NO_EVALUABLE:
                score += 5 / len(checks)
        return round(score, 2)

    def _manifest(self, contenidos: dict[str, str]) -> dict[str, object]:
        archivos = []
        for nombre, contenido in contenidos.items():
            archivos.append({
                "archivo": nombre,
                "sha256": self._hasher.sha256_texto(contenido),
            })
        return {"archivos": archivos}

    @staticmethod
    def render_markdown(
        *,
        plan: PlanAuditoria,
        branch: str | None,
        commit: str | None,
        checks: list[CheckAuditoria],
        global_result: str,
        score: float,
    ) -> str:
        filas = ["| Check | Estado | Severidad | Evidencias |", "|---|---|---|---|"]
        for check in checks:
            filas.append(
                f"| {check.id_check} | {check.estado.value} | {check.severidad.value} | {'; '.join(check.evidencia)} |"
            )

        backlog = [
            f"- [{check.id_check}] ({check.severidad.value}) {check.recomendacion}"
            for check in checks
            if check.estado == EstadoCheck.FAIL
        ]
        seccion_backlog = "\n".join(backlog) if backlog else "Sin backlog recomendado."

        return "\n".join(
            [
                f"# AUDITORÍA E2E ({plan.id_auditoria})",
                f"- Fecha UTC: {plan.fecha_utc.isoformat()}",
                f"- Branch: {branch or 'N/D'}",
                f"- Commit: {commit or 'N/D'}",
                "",
                "## Resumen",
                f"- Resultado global: **{global_result}**",
                f"- Scorecard: **{score}/10**",
                "",
                "## Tabla de checks",
                *filas,
                "",
                "## Backlog recomendado",
                seccion_backlog,
                "",
            ]
        )

"""Semilla idempotente (§8): usuario admin, patrones, rutinas, pruebas y alumnos de ejemplo.

Ejecutar con: python -m server.seed
"""
from __future__ import annotations

import sys

from sqlmodel import Session, select

from server.auth import hash_password, now_ms
from server.config import settings
from server.db import engine, init_db
from server.models import (
    Athlete,
    AthleteLevel,
    ExerciseVariant,
    Level,
    Pattern,
    RoutineBlock,
    RoutineDay,
    RoutineExercise,
    Test,
    User,
)

PATTERNS = [
    ("empuje", "Empuje", 1),
    ("traccion", "Tracción", 2),
    ("pierna", "Pierna", 3),
    ("carrera", "Carrera", 4),
    ("core", "Core", 5),
]

# Niveles por defecto (ids A/B/C heredados, nombres legibles, colores del prototipo).
LEVELS = [
    ("A", "Principiante", "#d8472b", 1),
    ("B", "Intermedio", "#e6a02c", 2),
    ("C", "Avanzado", "#3fae7a", 3),
]

# day_key → día de calendario (0=domingo..6=sábado) para resaltar "Hoy".
WEEKDAY = {"lunes": 1, "martes": 2, "miercoles": 3, "jueves": 4, "viernes": 5,
           "sabado": 6, "domingo": 0}

# Cada día: (day_key, name, focus, [bloques]).
# Cada bloque: (title, [ejercicios]); cada ejercicio: (name, pattern, A, B, C).
ROUTINES = [
    (
        "lunes", "Lunes", "Empuje + Core",
        [
            ("Bloque principal · 3 rondas", [
                ("Flexiones", "empuje", "Inclinadas en barra · 8–10", "Estándar al suelo · 8–12", "Diamante / pseudo-planche · 10–12"),
                ("Fondos", "empuje", "Banco, pies apoyados · 6–8", "En paralelas · 6–10", "Lastrados o tempo 3·1 · 8–10"),
                ("Empuje vertical", "empuje", "Pike manos altas · 6–8", "Pike al suelo · 8–10", "Pike elevado / a vertical · 6–8"),
                ("Core anti-extensión", "core", "Plancha 20–30 s", "Hollow 30–40 s", "Hollow + balanceo 40 s"),
            ]),
            ("Cierre · 5 min", [
                ("Trote suave + estiramiento", "empuje", "2×100 m + pectoral/hombro", "2×100 m + pectoral/hombro", "2×100 m + pectoral/hombro"),
            ]),
        ],
    ),
    (
        "martes", "Martes", "Carrera / Capacidad aeróbica",
        [
            ("Calentamiento", [
                ("Activación", "carrera", "Trote 5 min + movilidad", "Trote 6 min + 3 progresivos", "Trote 6 min + 4 progresivos"),
            ]),
            ("Bloque de series · por tiempo", [
                ("Intervalos", "carrera", "4×(2 min fuerte / 2 min suave)", "5×(2 min fuerte / 90 s suave)", "6×(2 min fuerte / 75 s suave)"),
            ]),
            ("Vuelta a la calma", [
                ("Regenerativo", "carrera", "Caminata 3 min + respiración", "Trote 4 min", "Trote 5 min"),
            ]),
        ],
    ),
    (
        "miercoles", "Miércoles", "Tracción + Core",
        [
            ("Bloque principal · 3 rondas", [
                ("Dominada", "traccion", "Remo australiano · 8–10", "Asistida / negativas · 4–6", "Estricta · 6–10"),
                ("Remo horizontal", "traccion", "Invertido pies al suelo · 8–10", "Invertido pies elevados · 8–12", "A una mano / archer · 6–8"),
                ("Agarre / colgado", "traccion", "Colgado pasivo 15–20 s", "Colgado activo 20–30 s", "Colgado + rodillas · 8–10"),
                ("Core anti-rotación", "core", "Plancha lateral 15–20 s", "Plancha lateral 25–35 s", "Lateral + elevación cadera · 8"),
            ]),
            ("Cierre · 5 min", [
                ("Movilidad hombro", "traccion", "Banda + dorsal/antebrazo", "Banda + dorsal/antebrazo", "Banda + dorsal/antebrazo"),
            ]),
        ],
    ),
    (
        "jueves", "Jueves", "Tren inferior + Potencia",
        [
            ("Parte A · Fuerza · 3 rondas", [
                ("Sentadilla", "pierna", "A banco / cajón · 10–12", "Libre profunda · 12–15", "Búlgara · 8–10/pierna"),
                ("Unilateral", "pierna", "Zancada estática asist. · 8", "Zancada caminando · 10", "Pistol asistido · 5–8"),
                ("Cadena posterior", "pierna", "Puente 2 piernas · 12–15", "Puente 1 pierna · 8–10", "Curl nórdico asist. · 5–8"),
            ]),
            ("Parte B · Potencia", [
                ("Salto", "pierna", "Cajón bajo · 5×3", "Vertical máximo · 5×3", "Drop jump · 5×3"),
                ("Aceleración", "carrera", "Sprint 20 m · 4", "Sprint 30 m · 5", "Sprint 40 m dinám. · 6"),
            ]),
        ],
    ),
    (
        "viernes", "Viernes", "Mixto / Game Day",
        [
            ("AMRAP 20 min · 5 estaciones", [
                ("1 · Empuje", "empuje", "Flexiones · 8", "Flexiones · 12", "Diamante · 12"),
                ("2 · Tracción", "traccion", "Remo australiano · 8", "Dominada asist. · 5", "Dominada estricta · 8"),
                ("3 · Pierna", "pierna", "Sentadilla · 12", "Zancada · 10/p", "Búlgara · 8/p"),
                ("4 · Carrera", "carrera", "Sprint 50 m", "Sprint 80 m", "Sprint 100 m"),
                ("5 · Core", "core", "Plancha 30 s", "Hollow 40 s", "Colgado + rodillas · 10"),
            ]),
        ],
    ),
]

TESTS = [
    ("flex", "Flexiones máximas", "empuje", "reps", "high"),
    ("dom", "Dominadas / remos máx.", "traccion", "reps", "high"),
    ("v700", "Vuelta 700 m", "carrera", "mm:ss", "low"),
    ("salto", "Salto vertical", "pierna", "cm", "high"),
    ("plancha", "Plancha / hollow máx.", "core", "seg", "high"),
]

ATHLETES = [
    ("Alumno 1", {"empuje": "B", "traccion": "A", "pierna": "B", "carrera": "B", "core": "A"}),
    ("Alumno 2", {"empuje": "A", "traccion": "A", "pierna": "A", "carrera": "A", "core": "A"}),
    ("Alumno 3", {"empuje": "C", "traccion": "B", "pierna": "C", "carrera": "B", "core": "B"}),
    ("Alumno 4", {"empuje": "B", "traccion": "C", "pierna": "A", "carrera": "C", "core": "B"}),
    ("Yo", {"empuje": "C", "traccion": "C", "pierna": "C", "carrera": "C", "core": "C"}),
]


def _seed_admin(session: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        print("  [!] ADMIN_EMAIL/ADMIN_PASSWORD no definidos: omito usuario admin.")
        return
    email = settings.admin_email.strip().lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        print(f"  [=] usuario admin ya existe ({email}), no se toca.")
        return
    session.add(
        User(email=email, password_hash=hash_password(settings.admin_password), created_at=now_ms())
    )
    session.commit()
    print(f"  [+] usuario admin creado: {email}")


def _seed_patterns(session: Session) -> None:
    for pid, label, sort in PATTERNS:
        if not session.get(Pattern, pid):
            session.add(Pattern(id=pid, label=label, sort=sort))
    session.commit()


def _seed_levels(session: Session) -> None:
    for lid, label, color, sort in LEVELS:
        if not session.get(Level, lid):
            session.add(Level(id=lid, label=label, color=color, sort=sort))
    session.commit()


def _seed_routines(session: Session) -> None:
    for sort_day, (day_key, name, focus, blocks) in enumerate(ROUTINES, start=1):
        if session.get(RoutineDay, day_key):
            continue  # idempotente: el día ya existe, no se re-siembra.
        session.add(RoutineDay(
            day_key=day_key, name=name, focus=focus, sort=sort_day, weekday=WEEKDAY.get(day_key)
        ))
        session.commit()
        for bsort, (title, exercises) in enumerate(blocks, start=1):
            block = RoutineBlock(day_key=day_key, title=title, sort=bsort)
            session.add(block)
            session.commit()
            session.refresh(block)
            for esort, (ename, pattern, va, vb, vc) in enumerate(exercises, start=1):
                ex = RoutineExercise(
                    block_id=block.id, name=ename, pattern_id=pattern, sort=esort,
                )
                session.add(ex)
                session.commit()
                session.refresh(ex)
                # Variantes relacionales por nivel A/B/C.
                for lid, txt in (("A", va), ("B", vb), ("C", vc)):
                    session.add(ExerciseVariant(exercise_id=ex.id, level_id=lid, text=txt, media=""))
            session.commit()


def _seed_tests(session: Session) -> None:
    for sort, (tid, name, pattern, unit, better) in enumerate(TESTS, start=1):
        if not session.get(Test, tid):
            session.add(
                Test(id=tid, name=name, pattern_id=pattern, unit=unit, better=better, sort=sort)
            )
    session.commit()


def _seed_athletes(session: Session) -> None:
    existing = session.exec(select(Athlete)).first()
    if existing:
        print("  [=] ya existen alumnos, no se siembran de ejemplo.")
        return
    for sort, (name, levels) in enumerate(ATHLETES, start=1):
        athlete = Athlete(name=name, sort=sort, created_at=now_ms())
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        for pid, level in levels.items():
            session.add(AthleteLevel(athlete_id=athlete.id, pattern_id=pid, level=level))
        session.commit()
    print(f"  [+] {len(ATHLETES)} alumnos de ejemplo creados.")


def run() -> None:
    init_db()
    with Session(engine) as session:
        print("Sembrando datos (idempotente)...")
        _seed_admin(session)
        _seed_patterns(session)
        _seed_levels(session)
        _seed_routines(session)
        _seed_tests(session)
        _seed_athletes(session)
        print("Seed completo.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"Error en el seed: {e}", file=sys.stderr)
        sys.exit(1)

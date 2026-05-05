"""Définition du questionnaire de profilage pour Orientation Mali.

Ce module contient les 10 questions du questionnaire qui évaluent les intérêts,
les forces, les matières préférées, les aspirations professionnelles, le style
d'apprentissage et les objectifs de l'étudiant.
"""

from src.orientation_mali.models.schemas import Question

QUESTIONNAIRE: list[Question] = [
    Question(
        id="q1",
        text="Quelles matières scolaires préférez-vous ? (Vous pouvez en citer plusieurs)",
        question_type="open",
    ),
    Question(
        id="q2",
        text="Dans quels domaines vous sentez-vous le plus compétent(e) ?",
        question_type="multiple_choice",
        options=[
            "Sciences et mathématiques",
            "Langues et littérature",
            "Sciences humaines et sociales",
            "Arts et créativité",
            "Technologie et informatique",
            "Commerce et gestion",
        ],
    ),
    Question(
        id="q3",
        text="Quel type d'activités aimez-vous faire en dehors de l'école ?",
        question_type="open",
    ),
    Question(
        id="q4",
        text="Quel métier ou domaine professionnel vous attire le plus ?",
        question_type="open",
    ),
    Question(
        id="q5",
        text="Comment préférez-vous apprendre ?",
        question_type="multiple_choice",
        options=[
            "En lisant et en écrivant",
            "En écoutant des explications",
            "En pratiquant et en expérimentant",
            "En travaillant en groupe",
            "En résolvant des problèmes seul(e)",
        ],
    ),
    Question(
        id="q6",
        text="Sur une échelle de 1 à 5, à quel point aimez-vous travailler avec les chiffres et les calculs ?",
        question_type="scale",
        options=["1", "2", "3", "4", "5"],
    ),
    Question(
        id="q7",
        text="Quels sont vos objectifs après l'obtention de votre diplôme ?",
        question_type="multiple_choice",
        options=[
            "Poursuivre des études universitaires",
            "Suivre une formation professionnelle courte",
            "Entrer directement dans le monde du travail",
            "Créer ma propre entreprise",
            "Je ne sais pas encore",
        ],
    ),
    Question(
        id="q8",
        text="Décrivez une situation où vous avez réussi quelque chose dont vous êtes fier(ère).",
        question_type="open",
    ),
    Question(
        id="q9",
        text="Préférez-vous travailler seul(e) ou en équipe ? Pourquoi ?",
        question_type="open",
    ),
    Question(
        id="q10",
        text="Si vous pouviez résoudre un problème dans votre communauté, lequel choisiriez-vous ?",
        question_type="open",
    ),
]

QUESTION_IDS: list[str] = [q.id for q in QUESTIONNAIRE]
"""Liste des identifiants de toutes les questions du questionnaire."""
